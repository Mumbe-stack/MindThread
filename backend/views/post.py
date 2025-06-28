from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from models import db, Post, User, Comment, Like, Vote
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

post_bp = Blueprint('posts', __name__)

def serialize_post(post, current_user_id=None, include_comments=False):
    """Serialize a post object to dictionary"""
    try:
        # Calculate vote score
        upvotes = Vote.query.filter_by(post_id=post.id, value=1).count()
        downvotes = Vote.query.filter_by(post_id=post.id, value=-1).count()
        vote_score = upvotes - downvotes
        
        # Get user's vote if logged in
        user_vote = None
        if current_user_id:
            user_vote_obj = Vote.query.filter_by(
                post_id=post.id, 
                user_id=current_user_id
            ).first()
            user_vote = user_vote_obj.value if user_vote_obj else None
        
        # Calculate likes
        likes_count = Like.query.filter_by(post_id=post.id).count()
        liked_by_user = False
        if current_user_id:
            user_like = Like.query.filter_by(
                post_id=post.id,
                user_id=current_user_id
            ).first()
            liked_by_user = user_like is not None
        
        # Get comments count
        comments_count = Comment.query.filter_by(post_id=post.id).count()
        
        # Get author info
        author = User.query.get(post.user_id)
        
        post_data = {
            'id': post.id,
            'title': post.title,
            'content': post.content,
            'user_id': post.user_id,
            'author': {
                'id': author.id if author else None,
                'username': author.username if author else 'Unknown',
                'email': author.email if author else None
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
        
        # Include comments if requested
        if include_comments:
            comments = Comment.query.filter_by(post_id=post.id).order_by(Comment.created_at.desc()).all()
            post_data['comments'] = [serialize_comment(comment) for comment in comments]
        
        return post_data
        
    except Exception as e:
        logger.error(f"Error serializing post {post.id}: {e}")
        # Return basic data if serialization fails
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

def serialize_comment(comment):
    """Serialize a comment object to dictionary"""
    author = User.query.get(comment.user_id)
    return {
        'id': comment.id,
        'content': comment.content,
        'user_id': comment.user_id,
        'post_id': comment.post_id,
        'parent_id': comment.parent_id,
        'author': {
            'id': author.id if author else None,
            'username': author.username if author else 'Unknown'
        } if author else None,
        'created_at': comment.created_at.isoformat() if comment.created_at else None,
        'updated_at': comment.updated_at.isoformat() if comment.updated_at else None,
        'is_approved': comment.is_approved,
        'is_flagged': comment.is_flagged
    }

@post_bp.route('/posts', methods=['GET'])
def get_posts():
    """Get all posts"""
    try:
        # Check if user is authenticated (optional for viewing posts)
        current_user_id = None
        try:
            verify_jwt_in_request(optional=True)
            current_user_id = get_jwt_identity()
        except Exception:
            pass  # Guest user
        
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 10, type=int), 100)  # Max 100 posts per page
        search = request.args.get('search', '').strip()
        sort_by = request.args.get('sort', 'created_at')  # created_at, vote_score, title
        order = request.args.get('order', 'desc')  # asc, desc
        
        # Build query
        query = Post.query.filter_by(is_approved=True)
        
        # Apply search filter
        if search:
            query = query.filter(
                db.or_(
                    Post.title.ilike(f'%{search}%'),
                    Post.content.ilike(f'%{search}%')
                )
            )
        
        # Apply sorting
        if sort_by == 'created_at':
            if order == 'desc':
                query = query.order_by(Post.created_at.desc())
            else:
                query = query.order_by(Post.created_at.asc())
        elif sort_by == 'title':
            if order == 'desc':
                query = query.order_by(Post.title.desc())
            else:
                query = query.order_by(Post.title.asc())
        elif sort_by == 'updated_at':
            if order == 'desc':
                query = query.order_by(Post.updated_at.desc())
            else:
                query = query.order_by(Post.updated_at.asc())
        else:
            # Default to created_at desc
            query = query.order_by(Post.created_at.desc())
        
        # Execute query
        posts = query.limit(per_page).offset((page - 1) * per_page).all()
        
        # Serialize posts
        serialized_posts = []
        for post in posts:
            try:
                serialized_post = serialize_post(post, current_user_id)
                serialized_posts.append(serialized_post)
            except Exception as e:
                logger.error(f"Error serializing post {post.id}: {e}")
                continue
        
        logger.info(f"Retrieved {len(serialized_posts)} posts for user {current_user_id or 'guest'}")
        return jsonify(serialized_posts), 200
        
    except Exception as e:
        logger.error(f"Error fetching posts: {e}")
        return jsonify({
            'error': 'Failed to fetch posts',
            'message': str(e)
        }), 500

@post_bp.route('/posts', methods=['POST'])
@jwt_required()
def create_post():
    """Create a new post"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        title = data.get('title', '').strip()
        content = data.get('content', '').strip()
        
        if not title:
            return jsonify({'error': 'Title is required'}), 400
        
        if not content:
            return jsonify({'error': 'Content is required'}), 400
        
        if len(title) > 200:
            return jsonify({'error': 'Title must be less than 200 characters'}), 400
        
        if len(content) > 10000:
            return jsonify({'error': 'Content must be less than 10,000 characters'}), 400
        
        # Create new post
        new_post = Post(
            title=title,
            content=content,
            user_id=current_user_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_approved=True,  # Auto-approve posts (you can change this logic)
            is_flagged=False
        )
        
        db.session.add(new_post)
        db.session.commit()
        
        # Return serialized post
        serialized_post = serialize_post(new_post, current_user_id)
        
        logger.info(f"User {current_user_id} created post {new_post.id}")
        return jsonify(serialized_post), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating post: {e}")
        return jsonify({
            'error': 'Failed to create post',
            'message': str(e)
        }), 500

@post_bp.route('/posts/<int:post_id>', methods=['GET'])
def get_post(post_id):
    """Get a specific post"""
    try:
        # Check if user is authenticated (optional)
        current_user_id = None
        try:
            verify_jwt_in_request(optional=True)
            current_user_id = get_jwt_identity()
        except Exception:
            pass
        
        post = Post.query.get(post_id)
        if not post:
            return jsonify({'error': 'Post not found'}), 404
        
        # Check if post is approved or if user is the author
        if not post.is_approved and post.user_id != current_user_id:
            return jsonify({'error': 'Post not found'}), 404
        
        serialized_post = serialize_post(post, current_user_id, include_comments=True)
        return jsonify(serialized_post), 200
        
    except Exception as e:
        logger.error(f"Error fetching post {post_id}: {e}")
        return jsonify({
            'error': 'Failed to fetch post',
            'message': str(e)
        }), 500

@post_bp.route('/posts/<int:post_id>', methods=['PATCH'])
@jwt_required()
def update_post(post_id):
    """Update a specific post"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        post = Post.query.get(post_id)
        if not post:
            return jsonify({'error': 'Post not found'}), 404
        
        # Check permissions (author or admin)
        if post.user_id != current_user_id and not current_user.is_admin:
            return jsonify({'error': 'Permission denied'}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Update fields if provided
        if 'title' in data:
            title = data['title'].strip()
            if not title:
                return jsonify({'error': 'Title cannot be empty'}), 400
            if len(title) > 200:
                return jsonify({'error': 'Title must be less than 200 characters'}), 400
            post.title = title
        
        if 'content' in data:
            content = data['content'].strip()
            if not content:
                return jsonify({'error': 'Content cannot be empty'}), 400
            if len(content) > 10000:
                return jsonify({'error': 'Content must be less than 10,000 characters'}), 400
            post.content = content
        
        # Admin-only fields
        if current_user.is_admin:
            if 'is_approved' in data:
                post.is_approved = bool(data['is_approved'])
            if 'is_flagged' in data:
                post.is_flagged = bool(data['is_flagged'])
        
        post.updated_at = datetime.utcnow()
        db.session.commit()
        
        serialized_post = serialize_post(post, current_user_id)
        
        logger.info(f"User {current_user_id} updated post {post_id}")
        return jsonify(serialized_post), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating post {post_id}: {e}")
        return jsonify({
            'error': 'Failed to update post',
            'message': str(e)
        }), 500

@post_bp.route('/posts/<int:post_id>', methods=['DELETE'])
@jwt_required()
def delete_post(post_id):
    """Delete a specific post"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        post = Post.query.get(post_id)
        if not post:
            return jsonify({'error': 'Post not found'}), 404
        
        # Check permissions (author or admin)
        if post.user_id != current_user_id and not current_user.is_admin:
            return jsonify({'error': 'Permission denied'}), 403
        
        # Delete related records first
        Like.query.filter_by(post_id=post_id).delete()
        Vote.query.filter_by(post_id=post_id).delete()
        Comment.query.filter_by(post_id=post_id).delete()
        
        # Delete the post
        db.session.delete(post)
        db.session.commit()
        
        logger.info(f"User {current_user_id} deleted post {post_id}")
        return jsonify({'message': 'Post deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting post {post_id}: {e}")
        return jsonify({
            'error': 'Failed to delete post',
            'message': str(e)
        }), 500

@post_bp.route('/posts/<int:post_id>/like', methods=['POST'])
@jwt_required()
def toggle_like(post_id):
    """Toggle like on a post"""
    try:
        current_user_id = get_jwt_identity()
        
        post = Post.query.get(post_id)
        if not post:
            return jsonify({'error': 'Post not found'}), 404
        
        # Check if user already liked this post
        existing_like = Like.query.filter_by(
            post_id=post_id,
            user_id=current_user_id
        ).first()
        
        if existing_like:
            # Unlike the post
            db.session.delete(existing_like)
            message = 'Post unliked'
        else:
            # Like the post
            new_like = Like(
                post_id=post_id,
                user_id=current_user_id,
                created_at=datetime.utcnow()
            )
            db.session.add(new_like)
            message = 'Post liked'
        
        db.session.commit()
        
        # Get updated like count
        likes_count = Like.query.filter_by(post_id=post_id).count()
        
        logger.info(f"User {current_user_id} toggled like on post {post_id}")
        return jsonify({
            'message': message,
            'likes': likes_count,
            'liked_by_user': not existing_like  # True if we just liked, False if we unliked
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error toggling like on post {post_id}: {e}")
        return jsonify({
            'error': 'Failed to toggle like',
            'message': str(e)
        }), 500

# Admin routes for post management
@post_bp.route('/posts/<int:post_id>/approve', methods=['PATCH'])
@jwt_required()
def approve_post(post_id):
    """Approve or reject a post (admin only)"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if not current_user or not current_user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        
        post = Post.query.get(post_id)
        if not post:
            return jsonify({'error': 'Post not found'}), 404
        
        data = request.get_json()
        is_approved = data.get('is_approved', True)
        
        post.is_approved = bool(is_approved)
        post.updated_at = datetime.utcnow()
        db.session.commit()
        
        action = 'approved' if is_approved else 'rejected'
        logger.info(f"Admin {current_user_id} {action} post {post_id}")
        
        return jsonify({
            'message': f'Post {action} successfully',
            'post': serialize_post(post, current_user_id)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error approving/rejecting post {post_id}: {e}")
        return jsonify({
            'error': 'Failed to update post approval status',
            'message': str(e)
        }), 500

@post_bp.route('/posts/<int:post_id>/flag', methods=['PATCH'])
@jwt_required()
def flag_post(post_id):
    """Flag or unflag a post"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        post = Post.query.get(post_id)
        if not post:
            return jsonify({'error': 'Post not found'}), 404
        
        data = request.get_json()
        is_flagged = data.get('is_flagged', True)
        
        # Regular users can only flag, admins can unflag
        if not is_flagged and not current_user.is_admin:
            return jsonify({'error': 'Only admins can unflag posts'}), 403
        
        post.is_flagged = bool(is_flagged)
        post.updated_at = datetime.utcnow()
        db.session.commit()
        
        action = 'flagged' if is_flagged else 'unflagged'
        logger.info(f"User {current_user_id} {action} post {post_id}")
        
        return jsonify({
            'message': f'Post {action} successfully',
            'post': serialize_post(post, current_user_id)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error flagging post {post_id}: {e}")
        return jsonify({
            'error': 'Failed to flag post',
            'message': str(e)
        }), 500
        
        
    # Add these endpoints to your post.py file

@post_bp.route("/posts/<int:post_id>/flag", methods=["POST"])
@jwt_required()
def flag_post(post_id):
    """Flag a post as inappropriate (admin only)"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if not current_user or not current_user.is_admin:
            return jsonify({"error": "Admin privileges required"}), 403

        post = Post.query.get(post_id)
        if not post:
            return jsonify({"error": "Post not found"}), 404

        # Flag the post
        if hasattr(post, 'is_flagged'):
            post.is_flagged = True
        if hasattr(post, 'flagged_at'):
            post.flagged_at = datetime.now(timezone.utc)
        if hasattr(post, 'updated_at'):
            post.updated_at = datetime.now(timezone.utc)

        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Post flagged successfully",
            "post": {
                "id": post.id,
                "title": post.title,
                "is_flagged": getattr(post, 'is_flagged', True)
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to flag post {post_id}: {e}")
        return jsonify({"error": "Failed to flag post"}), 500

@post_bp.route("/posts/<int:post_id>/unflag", methods=["POST"])
@jwt_required()
def unflag_post(post_id):
    """Remove flag from a post (admin only)"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if not current_user or not current_user.is_admin:
            return jsonify({"error": "Admin privileges required"}), 403

        post = Post.query.get(post_id)
        if not post:
            return jsonify({"error": "Post not found"}), 404

        # Unflag the post
        if hasattr(post, 'is_flagged'):
            post.is_flagged = False
        if hasattr(post, 'flagged_at'):
            post.flagged_at = None
        if hasattr(post, 'updated_at'):
            post.updated_at = datetime.now(timezone.utc)

        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Post unflagged successfully",
            "post": {
                "id": post.id,
                "title": post.title,
                "is_flagged": getattr(post, 'is_flagged', False)
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to unflag post {post_id}: {e}")
        return jsonify({"error": "Failed to unflag post"}), 500

@post_bp.route("/posts/<int:post_id>/approve", methods=["PATCH"])
@jwt_required()
def approve_post(post_id):
    """Approve a flagged post (admin only)"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if not current_user or not current_user.is_admin:
            return jsonify({"error": "Admin privileges required"}), 403

        post = Post.query.get(post_id)
        if not post:
            return jsonify({"error": "Post not found"}), 404

        data = request.get_json() or {}
        
        # Approve the post (remove flag)
        if hasattr(post, 'is_flagged'):
            post.is_flagged = False
        if hasattr(post, 'is_approved'):
            post.is_approved = data.get('is_approved', True)
        if hasattr(post, 'flagged_at'):
            post.flagged_at = None
        if hasattr(post, 'updated_at'):
            post.updated_at = datetime.now(timezone.utc)

        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Post approved successfully",
            "post": {
                "id": post.id,
                "title": post.title,
                "is_flagged": getattr(post, 'is_flagged', False),
                "is_approved": getattr(post, 'is_approved', True)
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to approve post {post_id}: {e}")
        return jsonify({"error": "Failed to approve post"}), 500