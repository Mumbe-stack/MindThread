from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from models import db, Post, User, Comment, Like, Vote
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

post_bp = Blueprint('posts', __name__)

def serialize_comment(comment):
    """Serialize a comment object to dict"""
    author = User.query.get(comment.user_id)
    return {
        'id': comment.id,
        'content': comment.content,
        'user_id': comment.user_id,
        'post_id': comment.post_id,
        'parent_id': comment.parent_id,
        'author': {
            'id': author.id,
            'username': author.username
        } if author else {"id": None, "username": "Unknown"},
        'created_at': comment.created_at.isoformat() if comment.created_at else None,
        'updated_at': comment.updated_at.isoformat() if comment.updated_at else None,
        'is_approved': comment.is_approved,
        'is_flagged': comment.is_flagged
    }

def serialize_post(post, current_user_id=None, include_comments=False):
    """Serialize a post object to dictionary"""
    try:
        upvotes = Vote.query.filter_by(post_id=post.id, value=1).count()
        downvotes = Vote.query.filter_by(post_id=post.id, value=-1).count()
        vote_score = upvotes - downvotes

        user_vote = None
        if current_user_id:
            uv = Vote.query.filter_by(post_id=post.id, user_id=current_user_id).first()
            user_vote = uv.value if uv else None

        likes_count = Like.query.filter_by(post_id=post.id).count()
        liked_by_user = False
        if current_user_id:
            liked_by_user = (
                Like.query.filter_by(post_id=post.id, user_id=current_user_id).first()
                is not None
            )

        comments_count = Comment.query.filter_by(post_id=post.id).count()
        author = User.query.get(post.user_id)

        data = {
            'id': post.id,
            'title': post.title,
            'content': post.content,
            'user_id': post.user_id,
            'author': {
                'id': author.id,
                'username': author.username,
                'email': author.email
            } if author else None,
            'created_at': post.created_at.isoformat() if post.created_at else None,
            'updated_at': post.updated_at.isoformat() if post.updated_at else None,
            'is_approved': post.is_approved,
            'is_flagged': post.is_flagged,
            'vote_score': vote_score,
            'upvotes': upvotes,
            'downvotes': downvotes,
            'total_votes': upvotes + downvotes,
            'userVote': user_vote,
            'likes': likes_count,
            'liked_by_user': liked_by_user,
            'comments_count': comments_count
        }

        if include_comments:
            comments = Comment.query.filter_by(post_id=post.id)\
                                    .order_by(Comment.created_at.desc())\
                                    .all()
            data['comments'] = [serialize_comment(c) for c in comments]

        return data

    except Exception as e:
        logger.error(f"Error serializing post {post.id}: {e}")
        return {
            'id': post.id,
            'title': post.title,
            'content': post.content,
            'user_id': post.user_id,
            'created_at': post.created_at.isoformat() if post.created_at else None,
            'updated_at': post.updated_at.isoformat() if post.updated_at else None,
            'is_approved': post.is_approved,
            'is_flagged': post.is_flagged,
            'vote_score': 0,
            'upvotes': 0,
            'downvotes': 0,
            'total_votes': 0,
            'likes': 0,
            'comments_count': 0
        }

@post_bp.route('/posts', methods=['GET'])
def get_posts():
    """Get all posts (with pagination, search, sorting)"""
    try:
        current_user_id = None
        try:
            verify_jwt_in_request(optional=True)
            current_user_id = get_jwt_identity()
        except:
            pass

        page    = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 10, type=int), 100)
        search  = request.args.get('search', '').strip()
        sort_by = request.args.get('sort', 'created_at')
        order   = request.args.get('order', 'desc')

        query = Post.query.filter_by(is_approved=True)

        if search:
            il = f"%{search}%"
            query = query.filter(
                db.or_(Post.title.ilike(il), Post.content.ilike(il))
            )

        sort_col = getattr(Post, sort_by, Post.created_at)
        query = query.order_by(
            getattr(sort_col, order.lower())()
        )

        posts = query.limit(per_page).offset((page-1)*per_page).all()
        result = [serialize_post(p, current_user_id) for p in posts]
        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Error fetching posts: {e}")
        return jsonify({'error': 'Failed to fetch posts', 'message': str(e)}), 500

@post_bp.route('/posts', methods=['POST'])
@jwt_required()
def create_post():
    """Create a new post"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json(silent=True)
        if not data:
            return jsonify({'error': 'No JSON body provided'}), 400

        title   = data.get('title','').strip()
        content = data.get('content','').strip()

        if not title:
            return jsonify({'error':'Title is required'}),400
        if not content:
            return jsonify({'error':'Content is required'}),400

        new_post = Post(
            title=title,
            content=content,
            user_id=current_user_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_approved=True,
            is_flagged=False
        )
        db.session.add(new_post)
        db.session.commit()

        return jsonify(serialize_post(new_post, current_user_id)), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating post: {e}")
        return jsonify({'error':'Failed to create post','message':str(e)}), 500

@post_bp.route('/posts/<int:post_id>', methods=['GET'])
def get_post(post_id):
    """Get a specific post (with comments)"""
    try:
        current_user_id = None
        try:
            verify_jwt_in_request(optional=True)
            current_user_id = get_jwt_identity()
        except:
            pass

        post = Post.query.get(post_id)
        if not post:
            return jsonify({'error':'Post not found'}),404
        if not post.is_approved and post.user_id!=current_user_id:
            return jsonify({'error':'Post not found'}),404

        return jsonify(serialize_post(post, current_user_id, include_comments=True)),200

    except Exception as e:
        logger.error(f"Error fetching post {post_id}: {e}")
        return jsonify({'error':'Failed to fetch post','message':str(e)}),500

@post_bp.route('/posts/<int:post_id>', methods=['PATCH'])
@jwt_required()
def update_post(post_id):
    """Update a specific post"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        post = Post.query.get(post_id)
        if not post:
            return jsonify({'error':'Post not found'}),404
        if post.user_id!=current_user_id and not current_user.is_admin:
            return jsonify({'error':'Permission denied'}),403

        data = request.get_json(silent=True)
        if not data:
            return jsonify({'error':'No JSON body provided'}),400

        if 'title' in data:
            title=data['title'].strip()
            if not title: return jsonify({'error':'Title cannot be empty'}),400
            post.title=title
        if 'content' in data:
            content=data['content'].strip()
            if not content: return jsonify({'error':'Content cannot be empty'}),400
            post.content=content
        if current_user.is_admin:
            if 'is_approved' in data: post.is_approved=bool(data['is_approved'])
            if 'is_flagged'  in data: post.is_flagged=bool(data['is_flagged'])

        post.updated_at=datetime.utcnow()
        db.session.commit()
        return jsonify(serialize_post(post,current_user_id)),200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating post {post_id}: {e}")
        return jsonify({'error':'Failed to update post','message':str(e)}),500

@post_bp.route('/posts/<int:post_id>', methods=['DELETE'])
@jwt_required()
def delete_post(post_id):
    """Delete a specific post"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        post = Post.query.get(post_id)
        if not post:
            return jsonify({'error':'Post not found'}),404
        if post.user_id!=current_user_id and not current_user.is_admin:
            return jsonify({'error':'Permission denied'}),403

        Like.query.filter_by(post_id=post_id).delete()
        Vote.query.filter_by(post_id=post_id).delete()
        Comment.query.filter_by(post_id=post_id).delete()
        db.session.delete(post)
        db.session.commit()
        return jsonify({'message':'Post deleted successfully'}),200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting post {post_id}: {e}")
        return jsonify({'error':'Failed to delete post','message':str(e)}),500

@post_bp.route('/posts/<int:post_id>/like', methods=['POST'])
@jwt_required()
def toggle_like(post_id):
    """Toggle like on a post"""
    try:
        current_user_id = get_jwt_identity()
        post = Post.query.get(post_id)
        if not post:
            return jsonify({'error':'Post not found'}),404

        existing = Like.query.filter_by(post_id=post_id,user_id=current_user_id).first()
        if existing:
            db.session.delete(existing)
            message='Post unliked'
        else:
            db.session.add(Like(post_id=post_id,user_id=current_user_id,created_at=datetime.utcnow()))
            message='Post liked'

        db.session.commit()
        likes_count = Like.query.filter_by(post_id=post_id).count()
        return jsonify({'message':message,'likes':likes_count,'liked_by_user':not bool(existing)}),200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error toggling like on post {post_id}: {e}")
        return jsonify({'error':'Failed to toggle like','message':str(e)}),500

# --- Admin routes ---

@post_bp.route('/api/admin/posts/<int:post_id>/approve', methods=['PATCH'])
@jwt_required()
def approve_post(post_id):
    """Approve or reject a post (admin only)"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        if not current_user or not current_user.is_admin:
            return jsonify({'error':'Admin access required'}),403

        post = Post.query.get(post_id)
        if not post:
            return jsonify({'error':'Post not found'}),404

        data = request.get_json(silent=True)
        if not data:
            return jsonify({'error':'No JSON body provided'}),400

        post.is_approved = bool(data.get('is_approved',True))
        post.updated_at = datetime.utcnow()
        db.session.commit()

        action = 'approved' if post.is_approved else 'rejected'
        return jsonify({'message':f'Post {action} successfully','post':serialize_post(post,current_user_id)}),200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error approving post {post_id}: {e}")
        return jsonify({'error':'Failed to update approval','message':str(e)}),500

@post_bp.route('/api/admin/posts/<int:post_id>/flag', methods=['PATCH'])
@jwt_required()
def admin_flag_post(post_id):
    """Flag or unflag a post (admin only)"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        if not current_user or not current_user.is_admin:
            return jsonify({'error':'Admin access required'}),403

        post = Post.query.get(post_id)
        if not post:
            return jsonify({'error':'Post not found'}),404

        data = request.get_json(silent=True)
        if not data:
            return jsonify({'error':'No JSON body provided'}),400

        post.is_flagged = bool(data.get('is_flagged',True))
        post.updated_at = datetime.utcnow()
        db.session.commit()

        action = 'flagged' if post.is_flagged else 'unflagged'
        return jsonify({'message':f'Post {action} successfully','post':serialize_post(post,current_user_id)}),200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error flagging post {post_id}: {e}")
        return jsonify({'error':'Failed to flag post','message':str(e)}),500
