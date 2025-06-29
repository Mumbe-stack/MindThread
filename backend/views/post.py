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
            'username': author.username,
            'avatar_url': author.avatar_url
        } if author else {"id": None, "username": "Unknown"},
        'created_at': comment.created_at.isoformat() if comment.created_at else None,
        'updated_at': comment.updated_at.isoformat() if comment.updated_at else None,
        'is_approved': comment.is_approved,
        'is_flagged': comment.is_flagged,
        'likes_count': comment.likes_count,
        'vote_score': comment.vote_score,
        'upvotes_count': comment.upvotes_count,
        'downvotes_count': comment.downvotes_count
    }

def serialize_post(post, current_user_id=None, include_comments=False):
    """Serialize a post object to dictionary"""
    try:
        # Get vote statistics
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

        # Get approved comments count only
        comments_count = Comment.query.filter_by(post_id=post.id, is_approved=True).count()
        author = User.query.get(post.user_id)

        data = {
            'id': post.id,
            'title': post.title,
            'content': post.content,
            'user_id': post.user_id,
            'username': author.username if author else "Unknown",  # Add username field
            'author': {
                'id': author.id,
                'username': author.username,
                'avatar_url': author.avatar_url
            } if author else {"id": None, "username": "Unknown"},
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
            'likes_count': likes_count,  # Add both for compatibility
            'liked_by_user': liked_by_user,
            'comments_count': comments_count
        }

        if include_comments:
            # Only include approved comments for regular users
            comments_query = Comment.query.filter_by(post_id=post.id)
            if current_user_id:
                current_user = User.query.get(current_user_id)
                if not (current_user and current_user.is_admin):
                    comments_query = comments_query.filter_by(is_approved=True)
            else:
                comments_query = comments_query.filter_by(is_approved=True)
            
            comments = comments_query.order_by(Comment.created_at.desc()).all()
            data['comments'] = [serialize_comment(c) for c in comments]

        return data

    except Exception as e:
        logger.error(f"Error serializing post {post.id}: {e}")
        return {
            'id': post.id,
            'title': post.title,
            'content': post.content,
            'user_id': post.user_id,
            'username': "Unknown",
            'author': {"id": None, "username": "Unknown"},
            'created_at': post.created_at.isoformat() if post.created_at else None,
            'updated_at': post.updated_at.isoformat() if post.updated_at else None,
            'is_approved': post.is_approved,
            'is_flagged': post.is_flagged,
            'vote_score': 0,
            'upvotes': 0,
            'downvotes': 0,
            'total_votes': 0,
            'likes': 0,
            'likes_count': 0,
            'comments_count': 0
        }

@post_bp.route('/posts', methods=['GET'])
def get_posts():
    """Get posts (approved only for regular users, all for admins)"""
    try:
        current_user_id = None
        current_user = None
        try:
            verify_jwt_in_request(optional=True)
            current_user_id = get_jwt_identity()
            if current_user_id:
                current_user = User.query.get(current_user_id)
        except:
            pass

        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 10, type=int), 100)
        search = request.args.get('search', '').strip()
        sort_by = request.args.get('sort', 'created_at')
        order = request.args.get('order', 'desc')

        # Base query with joins for author information
        query = Post.query.join(User, Post.user_id == User.id)

        # Filter by approval status based on user role
        if not (current_user and current_user.is_admin):
            # Regular users only see approved posts
            query = query.filter(Post.is_approved == True)

        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                db.or_(
                    Post.title.ilike(search_pattern), 
                    Post.content.ilike(search_pattern),
                    User.username.ilike(search_pattern)
                )
            )

        # Sorting
        sort_col = getattr(Post, sort_by, Post.created_at)
        if order.lower() == 'desc':
            query = query.order_by(sort_col.desc())
        else:
            query = query.order_by(sort_col.asc())

        posts = query.limit(per_page).offset((page-1)*per_page).all()
        result = [serialize_post(p, current_user_id) for p in posts]
        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Error fetching posts: {e}")
        return jsonify({'error': 'Failed to fetch posts', 'message': str(e)}), 500

@post_bp.route('/posts', methods=['POST'])
@jwt_required()
def create_post():
    """Create a new post (requires admin approval)"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        data = request.get_json(silent=True)
        if not data:
            return jsonify({'error': 'No JSON body provided'}), 400

        title = data.get('title','').strip()
        content = data.get('content','').strip()
        tags = data.get('tags', '').strip()

        if not title:
            return jsonify({'error':'Title is required'}), 400
        if not content:
            return jsonify({'error':'Content is required'}), 400

        # Posts require approval by default (except for admins)
        is_approved = current_user.is_admin if current_user else False

        new_post = Post(
            title=title,
            content=content,
            tags=tags,
            user_id=current_user_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_approved=is_approved,  # Requires approval unless admin
            is_flagged=False
        )
        db.session.add(new_post)
        db.session.commit()

        response_data = serialize_post(new_post, current_user_id)
        
        if not is_approved:
            response_data['message'] = 'Post created successfully and is pending admin approval'
        else:
            response_data['message'] = 'Post created and approved automatically'

        return jsonify(response_data), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating post: {e}")
        return jsonify({'error':'Failed to create post','message':str(e)}), 500

@post_bp.route('/posts/<int:post_id>', methods=['GET'])
def get_post(post_id):
    """Get a specific post (with comments)"""
    try:
        current_user_id = None
        current_user = None
        try:
            verify_jwt_in_request(optional=True)
            current_user_id = get_jwt_identity()
            if current_user_id:
                current_user = User.query.get(current_user_id)
        except:
            pass

        post = Post.query.get(post_id)
        if not post:
            return jsonify({'error':'Post not found'}), 404

        # Check if user can view this post
        can_view = (
            post.is_approved or  # Post is approved
            (current_user and current_user.is_admin) or  # User is admin
            (current_user_id == post.user_id)  # User is the author
        )

        if not can_view:
            return jsonify({'error':'Post not found'}), 404

        return jsonify(serialize_post(post, current_user_id, include_comments=True)), 200

    except Exception as e:
        logger.error(f"Error fetching post {post_id}: {e}")
        return jsonify({'error':'Failed to fetch post','message':str(e)}), 500

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
            'username': author.username,
            'avatar_url': author.avatar_url
        } if author else {"id": None, "username": "Unknown"},
        'created_at': comment.created_at.isoformat() if comment.created_at else None,
        'updated_at': comment.updated_at.isoformat() if comment.updated_at else None,
        'is_approved': comment.is_approved,
        'is_flagged': comment.is_flagged,
        'likes_count': comment.likes_count,
        'vote_score': comment.vote_score,
        'upvotes_count': comment.upvotes_count,
        'downvotes_count': comment.downvotes_count
    }

def serialize_post(post, current_user_id=None, include_comments=False):
    """Serialize a post object to dictionary"""
    try:
        # Get vote statistics
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

        # Get approved comments count only
        comments_count = Comment.query.filter_by(post_id=post.id, is_approved=True).count()
        author = User.query.get(post.user_id)

        data = {
            'id': post.id,
            'title': post.title,
            'content': post.content,
            'user_id': post.user_id,
            'username': author.username if author else "Unknown",  # Add username field
            'author': {
                'id': author.id,
                'username': author.username,
                'avatar_url': author.avatar_url
            } if author else {"id": None, "username": "Unknown"},
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
            'likes_count': likes_count,  # Add both for compatibility
            'liked_by_user': liked_by_user,
            'comments_count': comments_count
        }

        if include_comments:
            # Only include approved comments for regular users
            comments_query = Comment.query.filter_by(post_id=post.id)
            if current_user_id:
                current_user = User.query.get(current_user_id)
                if not (current_user and current_user.is_admin):
                    comments_query = comments_query.filter_by(is_approved=True)
            else:
                comments_query = comments_query.filter_by(is_approved=True)
            
            comments = comments_query.order_by(Comment.created_at.desc()).all()
            data['comments'] = [serialize_comment(c) for c in comments]

        return data

    except Exception as e:
        logger.error(f"Error serializing post {post.id}: {e}")
        return {
            'id': post.id,
            'title': post.title,
            'content': post.content,
            'user_id': post.user_id,
            'username': "Unknown",
            'author': {"id": None, "username": "Unknown"},
            'created_at': post.created_at.isoformat() if post.created_at else None,
            'updated_at': post.updated_at.isoformat() if post.updated_at else None,
            'is_approved': post.is_approved,
            'is_flagged': post.is_flagged,
            'vote_score': 0,
            'upvotes': 0,
            'downvotes': 0,
            'total_votes': 0,
            'likes': 0,
            'likes_count': 0,
            'comments_count': 0
        }

@post_bp.route('/posts', methods=['GET'])
def get_posts():
    """Get posts (approved only for regular users, all for admins)"""
    try:
        current_user_id = None
        current_user = None
        try:
            verify_jwt_in_request(optional=True)
            current_user_id = get_jwt_identity()
            if current_user_id:
                current_user = User.query.get(current_user_id)
        except:
            pass

        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 10, type=int), 100)
        search = request.args.get('search', '').strip()
        sort_by = request.args.get('sort', 'created_at')
        order = request.args.get('order', 'desc')

        # Base query with joins for author information
        query = Post.query.join(User, Post.user_id == User.id)

        # Filter by approval status based on user role
        if not (current_user and current_user.is_admin):
            # Regular users only see approved posts
            query = query.filter(Post.is_approved == True)

        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                db.or_(
                    Post.title.ilike(search_pattern), 
                    Post.content.ilike(search_pattern),
                    User.username.ilike(search_pattern)
                )
            )

        # Sorting
        sort_col = getattr(Post, sort_by, Post.created_at)
        if order.lower() == 'desc':
            query = query.order_by(sort_col.desc())
        else:
            query = query.order_by(sort_col.asc())

        posts = query.limit(per_page).offset((page-1)*per_page).all()
        result = [serialize_post(p, current_user_id) for p in posts]
        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Error fetching posts: {e}")
        return jsonify({'error': 'Failed to fetch posts', 'message': str(e)}), 500

@post_bp.route('/posts', methods=['POST'])
@jwt_required()
def create_post():
    """Create a new post (requires admin approval)"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        data = request.get_json(silent=True)
        if not data:
            return jsonify({'error': 'No JSON body provided'}), 400

        title = data.get('title','').strip()
        content = data.get('content','').strip()
        tags = data.get('tags', '').strip()

        if not title:
            return jsonify({'error':'Title is required'}), 400
        if not content:
            return jsonify({'error':'Content is required'}), 400

        # Posts require approval by default (except for admins)
        is_approved = current_user.is_admin if current_user else False

        new_post = Post(
            title=title,
            content=content,
            tags=tags,
            user_id=current_user_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_approved=is_approved,  # Requires approval unless admin
            is_flagged=False
        )
        db.session.add(new_post)
        db.session.commit()

        response_data = serialize_post(new_post, current_user_id)
        
        if not is_approved:
            response_data['message'] = 'Post created successfully and is pending admin approval'
        else:
            response_data['message'] = 'Post created and approved automatically'

        return jsonify(response_data), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating post: {e}")
        return jsonify({'error':'Failed to create post','message':str(e)}), 500

@post_bp.route('/posts/<int:post_id>', methods=['GET'])
def get_post(post_id):
    """Get a specific post (with comments)"""
    try:
        current_user_id = None
        current_user = None
        try:
            verify_jwt_in_request(optional=True)
            current_user_id = get_jwt_identity()
            if current_user_id:
                current_user = User.query.get(current_user_id)
        except:
            pass

        post = Post.query.get(post_id)
        if not post:
            return jsonify({'error':'Post not found'}), 404

        # Check if user can view this post
        can_view = (
            post.is_approved or  # Post is approved
            (current_user and current_user.is_admin) or  # User is admin
            (current_user_id == post.user_id)  # User is the author
        )

        if not can_view:
            return jsonify({'error':'Post not found'}), 404

        return jsonify(serialize_post(post, current_user_id, include_comments=True)), 200

    except Exception as e:
        logger.error(f"Error fetching post {post_id}: {e}")
        return jsonify({'error':'Failed to fetch post','message':str(e)}), 500

@post_bp.route('/posts/<int:post_id>', methods=['PATCH'])
@jwt_required()
def update_post(post_id):
    """Update a specific post — only allowed by the original author"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        post = Post.query.get(post_id)

        if not post:
            return jsonify({'error': 'Post not found'}), 404

        # Restrict strictly to post owner
        if post.user_id != current_user_id:
            return jsonify({'error': 'Permission denied'}), 403

        data = request.get_json(silent=True)
        if not data:
            return jsonify({'error': 'No JSON body provided'}), 400

        requires_reapproval = False

        if 'title' in data:
            title = data['title'].strip()
            if not title:
                return jsonify({'error': 'Title cannot be empty'}), 400
            if post.title != title:
                post.title = title
                requires_reapproval = True

        if 'content' in data:
            content = data['content'].strip()
            if not content:
                return jsonify({'error': 'Content cannot be empty'}), 400
            if post.content != content:
                post.content = content
                requires_reapproval = True

        if 'tags' in data:
            post.tags = data['tags'].strip() if data['tags'] else None

        # Non-admin users (which is now everyone here) require re-approval
        if requires_reapproval and post.is_approved:
            post.is_approved = False

        post.updated_at = datetime.utcnow()
        db.session.commit()

        response_data = serialize_post(post, current_user_id)
        if requires_reapproval:
            response_data['message'] = 'Post updated successfully and is pending admin approval'
        else:
            response_data['message'] = 'Post updated successfully'

        return jsonify(response_data), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating post {post_id}: {e}")
        return jsonify({'error': 'Failed to update post', 'message': str(e)}), 500


@post_bp.route('/posts/<int:post_id>', methods=['DELETE'])
@jwt_required()
def delete_post(post_id):
    """Delete a specific post"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        post = Post.query.get(post_id)
        
        if not post:
            return jsonify({'error':'Post not found'}), 404
        if post.user_id != current_user_id and not current_user.is_admin:
            return jsonify({'error':'Permission denied'}), 403

        # Delete related data first
        Like.query.filter_by(post_id=post_id).delete()
        Vote.query.filter_by(post_id=post_id).delete()
        Comment.query.filter_by(post_id=post_id).delete()
        
        db.session.delete(post)
        db.session.commit()
        return jsonify({'message':'Post deleted successfully'}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting post {post_id}: {e}")
        return jsonify({'error':'Failed to delete post','message':str(e)}), 500

@post_bp.route('/posts/<int:post_id>/like', methods=['POST'])
@jwt_required()
def toggle_like(post_id):
    """Toggle like on a post"""
    try:
        current_user_id = get_jwt_identity()
        post = Post.query.get(post_id)
        
        if not post:
            return jsonify({'error':'Post not found'}), 404

        existing = Like.query.filter_by(post_id=post_id, user_id=current_user_id).first()
        if existing:
            db.session.delete(existing)
            message = 'Post unliked'
            liked = False
        else:
            new_like = Like(
                post_id=post_id,
                user_id=current_user_id,
                created_at=datetime.utcnow()
            )
            db.session.add(new_like)
            message = 'Post liked'
            liked = True

        db.session.commit()
        
        likes_count = Like.query.filter_by(post_id=post_id).count()
        return jsonify({
            'message': message,
            'likes': likes_count,
            'likes_count': likes_count,
            'liked_by_user': liked
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error toggling like on post {post_id}: {e}")
        return jsonify({'error':'Failed to toggle like','message':str(e)}), 500

# ============== ADMIN ROUTES ==============

@post_bp.route('/admin/posts', methods=['GET'])
@jwt_required()
def admin_get_all_posts():
    """Admin: Get all posts (approved and unapproved)"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if not current_user or not current_user.is_admin:
            return jsonify({'error':'Admin access required'}), 403

        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        status = request.args.get('status', 'all')  # 'all', 'approved', 'unapproved', 'flagged'

        query = Post.query.join(User, Post.user_id == User.id)

        # Filter by status
        if status == 'approved':
            query = query.filter(Post.is_approved == True)
        elif status == 'unapproved':
            query = query.filter(Post.is_approved == False)
        elif status == 'flagged':
            query = query.filter(Post.is_flagged == True)

        query = query.order_by(Post.created_at.desc())
        posts = query.limit(per_page).offset((page-1)*per_page).all()
        
        result = [serialize_post(p, current_user_id) for p in posts]
        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Error fetching admin posts: {e}")
        return jsonify({'error':'Failed to fetch posts','message':str(e)}), 500

@post_bp.route('/admin/posts/<int:post_id>/approve', methods=['PATCH'])
@jwt_required()
def approve_post(post_id):
    """Admin: Approve or reject a post"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if not current_user or not current_user.is_admin:
            return jsonify({'error':'Admin access required'}), 403

        post = Post.query.get(post_id)
        if not post:
            return jsonify({'error':'Post not found'}), 404

        data = request.get_json(silent=True)
        if not data:
            return jsonify({'error':'No JSON body provided'}), 400

        is_approved = bool(data.get('is_approved', True))
        post.is_approved = is_approved
        post.updated_at = datetime.utcnow()
        
        # If rejecting, optionally add a reason
        if not is_approved and 'reason' in data:
            # Could store rejection reason in a separate table if needed
            pass

        db.session.commit()

        action = 'approved' if is_approved else 'rejected'
        return jsonify({
            'message': f'Post {action} successfully',
            'post': serialize_post(post, current_user_id)
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error approving post {post_id}: {e}")
        return jsonify({'error':'Failed to update approval','message':str(e)}), 500

@post_bp.route('/admin/posts/<int:post_id>/flag', methods=['PATCH'])
@jwt_required()
def admin_flag_post(post_id):
    """Admin: Flag or unflag a post"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if not current_user or not current_user.is_admin:
            return jsonify({'error':'Admin access required'}), 403

        post = Post.query.get(post_id)
        if not post:
            return jsonify({'error':'Post not found'}), 404

        data = request.get_json(silent=True)
        is_flagged = bool(data.get('is_flagged', True)) if data else True

        post.is_flagged = is_flagged
        post.updated_at = datetime.utcnow()
        db.session.commit()

        action = 'flagged' if is_flagged else 'unflagged'
        return jsonify({
            'message': f'Post {action} successfully',
            'post': serialize_post(post, current_user_id)
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error flagging post {post_id}: {e}")
        return jsonify({'error':'Failed to flag post','message':str(e)}), 500

@post_bp.route('/admin/posts/unapproved', methods=['GET'])
@jwt_required()
def get_unapproved_posts():
    """Admin: Get all unapproved posts"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if not current_user or not current_user.is_admin:
            return jsonify({'error':'Admin access required'}), 403

        posts = Post.query.join(User, Post.user_id == User.id)\
                         .filter(Post.is_approved == False)\
                         .order_by(Post.created_at.desc())\
                         .all()
        
        result = [serialize_post(p, current_user_id) for p in posts]
        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Error fetching unapproved posts: {e}")
        return jsonify({'error':'Failed to fetch posts','message':str(e)}), 500


@post_bp.route('/posts/<int:post_id>', methods=['DELETE'])
@jwt_required()
def delete_post(post_id):
    """Delete a specific post"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        post = Post.query.get(post_id)
        
        if not post:
            return jsonify({'error':'Post not found'}), 404
        if post.user_id != current_user_id and not current_user.is_admin:
            return jsonify({'error':'Permission denied'}), 403

        # Delete related data first
        Like.query.filter_by(post_id=post_id).delete()
        Vote.query.filter_by(post_id=post_id).delete()
        Comment.query.filter_by(post_id=post_id).delete()
        
        db.session.delete(post)
        db.session.commit()
        return jsonify({'message':'Post deleted successfully'}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting post {post_id}: {e}")
        return jsonify({'error':'Failed to delete post','message':str(e)}), 500

@post_bp.route('/posts/<int:post_id>/like', methods=['POST'])
@jwt_required()
def toggle_like(post_id):
    """Toggle like on a post"""
    try:
        current_user_id = get_jwt_identity()
        post = Post.query.get(post_id)
        
        if not post:
            return jsonify({'error':'Post not found'}), 404

        existing = Like.query.filter_by(post_id=post_id, user_id=current_user_id).first()
        if existing:
            db.session.delete(existing)
            message = 'Post unliked'
            liked = False
        else:
            new_like = Like(
                post_id=post_id,
                user_id=current_user_id,
                created_at=datetime.utcnow()
            )
            db.session.add(new_like)
            message = 'Post liked'
            liked = True

        db.session.commit()
        
        likes_count = Like.query.filter_by(post_id=post_id).count()
        return jsonify({
            'message': message,
            'likes': likes_count,
            'likes_count': likes_count,
            'liked_by_user': liked
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error toggling like on post {post_id}: {e}")
        return jsonify({'error':'Failed to toggle like','message':str(e)}), 500

# ============== ADMIN ROUTES ==============

@post_bp.route('/admin/posts', methods=['GET'])
@jwt_required()
def admin_get_all_posts():
    """Admin: Get all posts (approved and unapproved)"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if not current_user or not current_user.is_admin:
            return jsonify({'error':'Admin access required'}), 403

        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        status = request.args.get('status', 'all')  # 'all', 'approved', 'unapproved', 'flagged'

        query = Post.query.join(User, Post.user_id == User.id)

        # Filter by status
        if status == 'approved':
            query = query.filter(Post.is_approved == True)
        elif status == 'unapproved':
            query = query.filter(Post.is_approved == False)
        elif status == 'flagged':
            query = query.filter(Post.is_flagged == True)

        query = query.order_by(Post.created_at.desc())
        posts = query.limit(per_page).offset((page-1)*per_page).all()
        
        result = [serialize_post(p, current_user_id) for p in posts]
        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Error fetching admin posts: {e}")
        return jsonify({'error':'Failed to fetch posts','message':str(e)}), 500

@post_bp.route('/admin/posts/<int:post_id>/approve', methods=['PATCH'])
@jwt_required()
def approve_post(post_id):
    """Admin: Approve or reject a post"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if not current_user or not current_user.is_admin:
            return jsonify({'error':'Admin access required'}), 403

        post = Post.query.get(post_id)
        if not post:
            return jsonify({'error':'Post not found'}), 404

        data = request.get_json(silent=True)
        if not data:
            return jsonify({'error':'No JSON body provided'}), 400

        is_approved = bool(data.get('is_approved', True))
        post.is_approved = is_approved
        post.updated_at = datetime.utcnow()
        
        # If rejecting, optionally add a reason
        if not is_approved and 'reason' in data:
            # Could store rejection reason in a separate table if needed
            pass

        db.session.commit()

        action = 'approved' if is_approved else 'rejected'
        return jsonify({
            'message': f'Post {action} successfully',
            'post': serialize_post(post, current_user_id)
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error approving post {post_id}: {e}")
        return jsonify({'error':'Failed to update approval','message':str(e)}), 500

@post_bp.route('/admin/posts/<int:post_id>/flag', methods=['PATCH'])
@jwt_required()
def admin_flag_post(post_id):
    """Admin: Flag or unflag a post"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if not current_user or not current_user.is_admin:
            return jsonify({'error':'Admin access required'}), 403

        post = Post.query.get(post_id)
        if not post:
            return jsonify({'error':'Post not found'}), 404

        data = request.get_json(silent=True)
        is_flagged = bool(data.get('is_flagged', True)) if data else True

        post.is_flagged = is_flagged
        post.updated_at = datetime.utcnow()
        db.session.commit()

        action = 'flagged' if is_flagged else 'unflagged'
        return jsonify({
            'message': f'Post {action} successfully',
            'post': serialize_post(post, current_user_id)
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error flagging post {post_id}: {e}")
        return jsonify({'error':'Failed to flag post','message':str(e)}), 500

@post_bp.route('/admin/posts/unapproved', methods=['GET'])
@jwt_required()
def get_unapproved_posts():
    """Admin: Get all unapproved posts"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if not current_user or not current_user.is_admin:
            return jsonify({'error':'Admin access required'}), 403

        posts = Post.query.join(User, Post.user_id == User.id)\
                         .filter(Post.is_approved == False)\
                         .order_by(Post.created_at.desc())\
                         .all()
        
        result = [serialize_post(p, current_user_id) for p in posts]
        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Error fetching unapproved posts: {e}")
        return jsonify({'error':'Failed to fetch posts','message':str(e)}), 500