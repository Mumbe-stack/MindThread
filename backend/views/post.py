from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    jwt_required,
    get_jwt_identity,
    verify_jwt_in_request,
)
from models import db, Post, User, Comment, Like, Vote
from sqlalchemy import or_
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

post_bp = Blueprint('posts', __name__)

def serialize_comment(comment):
    """Serialize a comment object to dict"""
    author = User.query.get(comment.user_id)
    return {
        'id': comment.id,
        'content': comment.content,
        'post_id': comment.post_id,
        'parent_id': comment.parent_id,
        'author': {
            'id': author.id,
            'username': author.username
        } if author else None,
        'created_at': comment.created_at.isoformat() if comment.created_at else None,
        'updated_at': comment.updated_at.isoformat() if comment.updated_at else None,
        'is_approved': comment.is_approved,
        'is_flagged': comment.is_flagged,
        'likes_count': comment.likes.count(),
        'vote_score': sum(v.value for v in comment.votes),
        'upvotes': comment.votes.filter_by(value=1).count(),
        'downvotes': comment.votes.filter_by(value=-1).count(),
        'total_votes': comment.votes.count(),
        'replies_count': comment.replies.filter_by(is_approved=True).count()
    }

def serialize_post(post, current_user_id=None, include_comments=False):
    """Serialize a post object to dict"""
    # build basic vote & like metrics
    upvotes = Vote.query.filter_by(post_id=post.id, value=1).count()
    downvotes = Vote.query.filter_by(post_id=post.id, value=-1).count()
    vote_score = upvotes - downvotes
    likes_count = Like.query.filter_by(post_id=post.id).count()

    # determine user-specific flags
    user_vote = None
    liked_by_user = False
    current_user = None
    if current_user_id:
        current_user = User.query.get(current_user_id)
        uv = Vote.query.filter_by(post_id=post.id, user_id=current_user_id).first()
        user_vote = uv.value if uv else None
        liked_by_user = (
            Like.query
                .filter_by(post_id=post.id, user_id=current_user_id)
                .first() is not None
        )

    # comment count (only approved for non-admins)
    if current_user and current_user.is_admin:
        comments_count = Comment.query.filter_by(post_id=post.id).count()
    else:
        comments_count = Comment.query.filter_by(
            post_id=post.id, is_approved=True
        ).count()

    author = User.query.get(post.user_id)

    data = {
        'id': post.id,
        'title': post.title,
        'content': post.content,
        'tags': post.tags,
        'author': {
            'id': author.id,
            'username': author.username
        } if author else None,
        'created_at': post.created_at.isoformat() if post.created_at else None,
        'updated_at': post.updated_at.isoformat() if post.updated_at else None,
        'is_approved': post.is_approved,
        'is_flagged': post.is_flagged,
        'upvotes': upvotes,
        'downvotes': downvotes,
        'vote_score': vote_score,
        'total_votes': upvotes + downvotes,
        'likes_count': likes_count,
        'likes': likes_count,
        'liked_by_user': liked_by_user,
        'user_vote': user_vote,
        'comments_count': comments_count
    }

    # include nested comments if requested
    if include_comments:
        q = Comment.query.filter_by(post_id=post.id)
        if not (current_user and current_user.is_admin):
            q = q.filter_by(is_approved=True)
        comments = q.order_by(Comment.created_at.desc()).all()
        data['comments'] = [serialize_comment(c) for c in comments]

    return data


@post_bp.route('/posts', methods=['GET'])
def get_posts():
    """List approved posts (optional pagination, search, sort)"""
    try:
        # optional auth
        current_user_id = None
        try:
            verify_jwt_in_request(optional=True)
            current_user_id = get_jwt_identity()
        except Exception:
            pass

        # query params
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 10, type=int), 100)
        search = request.args.get('search', '', type=str).strip()
        sort_by = request.args.get('sort', 'created_at', type=str)
        order = request.args.get('order', 'desc', type=str)

        # base query: only approved
        query = Post.query.filter_by(is_approved=True)

        if search:
            query = query.filter(
                or_(
                    Post.title.ilike(f'%{search}%'),
                    Post.content.ilike(f'%{search}%')
                )
            )

        # sorting
        if sort_by == 'title':
            query = query.order_by(
                Post.title.desc() if order == 'desc' else Post.title.asc()
            )
        elif sort_by == 'updated_at':
            query = query.order_by(
                Post.updated_at.desc() if order == 'desc' else Post.updated_at.asc()
            )
        else:
            # default: sort by created_at
            query = query.order_by(
                Post.created_at.desc() if order == 'desc' else Post.created_at.asc()
            )

        posts = query.offset((page - 1) * per_page).limit(per_page).all()

        result = [serialize_post(p, current_user_id) for p in posts]

        logger.info(f"Fetched {len(result)} posts (user={current_user_id or 'guest'})")
        return jsonify(result), 200

    except Exception as e:
        logger.error(f"get_posts error: {e}")
        return jsonify({'error': 'Could not fetch posts'}), 500


@post_bp.route('/posts', methods=['POST'])
@jwt_required()
def create_post():
    """Create a new post"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}

        title = data.get('title', '').strip()
        content = data.get('content', '').strip()

        if not title:
            return jsonify({'error': 'Title is required'}), 400
        if len(title) > 200:
            return jsonify({'error': 'Title too long'}), 400
        if not content:
            return jsonify({'error': 'Content is required'}), 400
        if len(content) > 10000:
            return jsonify({'error': 'Content too long'}), 400

        post = Post(
            title=title,
            content=content,
            tags=data.get('tags'),
            user_id=user_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            is_approved=True,
            is_flagged=False
        )
        db.session.add(post)
        db.session.commit()

        logger.info(f"User {user_id} created post {post.id}")
        return jsonify(serialize_post(post, user_id)), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"create_post error: {e}")
        return jsonify({'error': 'Could not create post'}), 500


@post_bp.route('/posts/<int:post_id>', methods=['GET'])
def get_post(post_id):
    """Get a single post, with comments"""
    try:
        current_user_id = None
        try:
            verify_jwt_in_request(optional=True)
            current_user_id = get_jwt_identity()
        except Exception:
            pass

        post = Post.query.get(post_id)
        if not post or (not post.is_approved and post.user_id != current_user_id):
            return jsonify({'error': 'Post not found'}), 404

        data = serialize_post(post, current_user_id, include_comments=True)
        return jsonify(data), 200

    except Exception as e:
        logger.error(f"get_post error: {e}")
        return jsonify({'error': 'Could not fetch post'}), 500


@post_bp.route('/posts/<int:post_id>', methods=['PATCH'])
@jwt_required()
def update_post(post_id):
    """Update post (author or admin)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        post = Post.query.get(post_id)
        if not post:
            return jsonify({'error': 'Not found'}), 404
        if post.user_id != user_id and not user.is_admin:
            return jsonify({'error': 'Forbidden'}), 403

        data = request.get_json() or {}
        if 'title' in data:
            t = data['title'].strip()
            if not t: return jsonify({'error': 'Title empty'}), 400
            if len(t) > 200: return jsonify({'error': 'Title too long'}), 400
            post.title = t
        if 'content' in data:
            c = data['content'].strip()
            if not c: return jsonify({'error': 'Content empty'}), 400
            if len(c) > 10000: return jsonify({'error': 'Content too long'}), 400
            post.content = c

        # admin can override approval/flag
        if user.is_admin:
            if 'is_approved' in data:
                post.is_approved = bool(data['is_approved'])
            if 'is_flagged' in data:
                post.is_flagged = bool(data['is_flagged'])

        post.updated_at = datetime.now(timezone.utc)
        db.session.commit()

        return jsonify(serialize_post(post, user_id)), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"update_post error: {e}")
        return jsonify({'error': 'Could not update'}), 500


@post_bp.route('/posts/<int:post_id>', methods=['DELETE'])
@jwt_required()
def delete_post(post_id):
    """Delete post (author or admin)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        post = Post.query.get(post_id)
        if not post:
            return jsonify({'error': 'Not found'}), 404
        if post.user_id != user_id and not user.is_admin:
            return jsonify({'error': 'Forbidden'}), 403

        # cascade deletes via relationships
        db.session.delete(post)
        db.session.commit()

        return jsonify({'message': 'Deleted'}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"delete_post error: {e}")
        return jsonify({'error': 'Could not delete'}), 500


@post_bp.route('/posts/<int:post_id>/like', methods=['POST'])
@jwt_required()
def toggle_like(post_id):
    """Like or unlike a post"""
    try:
        user_id = get_jwt_identity()
        post = Post.query.get(post_id)
        if not post:
            return jsonify({'error': 'Not found'}), 404

        existing = Like.query.filter_by(post_id=post_id, user_id=user_id).first()
        if existing:
            db.session.delete(existing)
            action = 'unliked'
        else:
            like = Like(
                post_id=post_id,
                user_id=user_id,
                created_at=datetime.now(timezone.utc)
            )
            db.session.add(like)
            action = 'liked'

        db.session.commit()
        count = Like.query.filter_by(post_id=post_id).count()
        return jsonify({
            'message': f'Post {action}',
            'likes_count': count,
            'liked_by_user': action == 'liked'
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"toggle_like error: {e}")
        return jsonify({'error': 'Could not toggle like'}), 500


@post_bp.route('/posts/<int:post_id>/approve', methods=['PATCH'])
@jwt_required()
def approve_post(post_id):
    """Approve or reject a post (admin only)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user or not user.is_admin:
            return jsonify({'error': 'Admin only'}), 403

        post = Post.query.get(post_id)
        if not post:
            return jsonify({'error': 'Not found'}), 404

        data = request.get_json() or {}
        post.is_approved = bool(data.get('is_approved', True))
        post.updated_at = datetime.now(timezone.utc)
        db.session.commit()

        status = 'approved' if post.is_approved else 'rejected'
        return jsonify({
            'message': f'Post {status}',
            'post': serialize_post(post, user_id)
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"approve_post error: {e}")
        return jsonify({'error': 'Could not set approval'}), 500


@post_bp.route('/posts/<int:post_id>/flag', methods=['PATCH'])
@jwt_required()
def flag_post(post_id):
    """Flag or unflag a post"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        post = Post.query.get(post_id)
        if not post:
            return jsonify({'error': 'Not found'}), 404

        data = request.get_json() or {}
        flag = bool(data.get('is_flagged', True))

        if not flag and not (user and user.is_admin):
            return jsonify({'error': 'Admin only to unflag'}), 403

        post.is_flagged = flag
        post.updated_at = datetime.now(timezone.utc)
        db.session.commit()

        status = 'flagged' if post.is_flagged else 'unflagged'
        return jsonify({
            'message': f'Post {status}',
            'post': serialize_post(post, user_id)
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"flag_post error: {e}")
        return jsonify({'error': 'Could not set flag'}), 500