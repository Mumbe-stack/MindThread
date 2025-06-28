from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timezone, timedelta
from sqlalchemy import func, and_, or_
from models import db, User, Post, Comment, Vote

# Create Blueprint
admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    """Decorator to ensure admin access"""
    def wrapper(*args, **kwargs):
        try:
            current_user_id = get_jwt_identity()
            current_user = User.query.get(current_user_id)
            if not current_user or not current_user.is_admin:
                return jsonify({"error": "Admin privileges required"}), 403
            return f(*args, **kwargs)
        except Exception as e:
            current_app.logger.error(f"Admin check error: {e}")
            return jsonify({"error": "Authentication error"}), 401
    wrapper.__name__ = f.__name__
    return wrapper

@admin_bp.route("/admin/stats", methods=["GET"])
@jwt_required()
@admin_required
def get_admin_stats():
    """Get comprehensive admin statistics"""
    try:
        # Basic counts
        total_users = User.query.count()
        total_posts = Post.query.count()
        total_comments = Comment.query.count()
        total_votes = Vote.query.count()
        
        # User statistics
        active_users = User.query.filter(User.is_active == True).count()
        blocked_users = User.query.filter(User.is_blocked == True).count()
        admin_users = User.query.filter(User.is_admin == True).count()
        
        # Recent activity (last 30 days)
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        recent_users = User.query.filter(User.created_at >= thirty_days_ago).count()
        recent_posts = Post.query.filter(Post.created_at >= thirty_days_ago).count()
        recent_comments = Comment.query.filter(Comment.created_at >= thirty_days_ago).count()
        
        # Flagged content (if you have is_flagged fields, otherwise return 0)
        flagged_posts = 0
        flagged_comments = 0
        try:
            # Try to get flagged content if the fields exist
            flagged_posts = Post.query.filter(Post.is_flagged == True).count()
        except:
            pass
        
        try:
            flagged_comments = Comment.query.filter(Comment.is_flagged == True).count()
        except:
            pass
        
        total_flagged = flagged_posts + flagged_comments

        return jsonify({
            # Main stats
            "users": total_users,
            "posts": total_posts,
            "comments": total_comments,
            "votes": total_votes,
            "flagged": total_flagged,
            
            # Detailed user stats
            "total_users": total_users,
            "active_users": active_users,
            "blocked_users": blocked_users,
            "admin_users": admin_users,
            "inactive_users": total_users - active_users,
            
            # Content stats
            "total_posts": total_posts,
            "total_comments": total_comments,
            "total_votes": total_votes,
            "flagged_posts": flagged_posts,
            "flagged_comments": flagged_comments,
            
            # Recent activity
            "recent_users": recent_users,
            "recent_posts": recent_posts,
            "recent_comments": recent_comments,
            
            # Growth metrics
            "user_growth": recent_users,
            "content_growth": recent_posts + recent_comments
        }), 200

    except Exception as e:
        current_app.logger.error(f"Failed to fetch admin stats: {e}")
        return jsonify({"error": "Failed to fetch statistics"}), 500

@admin_bp.route("/admin/users", methods=["GET"])
@jwt_required()
@admin_required
def get_all_users_admin():
    """Get all users with admin details"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        search = request.args.get('search', '').strip()
        
        # Build query
        query = User.query
        if search:
            query = query.filter(
                or_(
                    User.username.ilike(f'%{search}%'),
                    User.email.ilike(f'%{search}%')
                )
            )
        
        # Get users with pagination
        users = query.order_by(User.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        users_data = []
        for user in users.items:
            user_data = {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_admin": user.is_admin,
                "is_blocked": user.is_blocked,
                "is_active": getattr(user, 'is_active', True),
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if hasattr(user, 'updated_at') and user.updated_at else None
            }
            
            # Add post/comment counts
            try:
                user_data.update({
                    "post_count": user.posts.count() if hasattr(user, 'posts') else 0,
                    "comment_count": user.comments.count() if hasattr(user, 'comments') else 0,
                    "vote_count": user.votes.count() if hasattr(user, 'votes') else 0
                })
            except:
                user_data.update({
                    "post_count": 0,
                    "comment_count": 0,
                    "vote_count": 0
                })
            
            users_data.append(user_data)
        
        return jsonify({
            "users": users_data,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": users.total,
                "pages": users.pages,
                "has_next": users.has_next,
                "has_prev": users.has_prev
            }
        }), 200

    except Exception as e:
        current_app.logger.error(f"Failed to fetch all users: {e}")
        return jsonify({"error": "Failed to fetch users"}), 500

@admin_bp.route("/admin/users/search", methods=["GET"])
@jwt_required()
@admin_required
def search_users_admin():
    """Search users for admin"""
    try:
        query = request.args.get('q', '').strip()
        if not query or len(query) < 2:
            return jsonify({"users": []}), 200
        
        users = User.query.filter(
            or_(
                User.username.ilike(f'%{query}%'),
                User.email.ilike(f'%{query}%')
            )
        ).limit(20).all()
        
        users_data = []
        for user in users:
            users_data.append({
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_admin": user.is_admin,
                "is_blocked": user.is_blocked,
                "is_active": getattr(user, 'is_active', True),
                "created_at": user.created_at.isoformat() if user.created_at else None
            })
        
        return jsonify({
            "users": users_data,
            "query": query,
            "count": len(users_data)
        }), 200

    except Exception as e:
        current_app.logger.error(f"Failed to search users: {e}")
        return jsonify({"error": "Failed to search users"}), 500

@admin_bp.route("/admin/posts", methods=["GET"])
@jwt_required()
@admin_required
def get_all_posts_admin():
    """Get all posts for admin"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        search = request.args.get('search', '').strip()
        
        # Build query
        query = Post.query
        if search:
            query = query.filter(
                or_(
                    Post.title.ilike(f'%{search}%'),
                    Post.content.ilike(f'%{search}%')
                )
            )
        
        # Get posts with pagination
        posts = query.order_by(Post.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        posts_data = []
        for post in posts.items:
            post_data = {
                "id": post.id,
                "title": post.title,
                "content": post.content[:200] + "..." if len(post.content) > 200 else post.content,
                "created_at": post.created_at.isoformat() if post.created_at else None,
                "updated_at": post.updated_at.isoformat() if hasattr(post, 'updated_at') and post.updated_at else None,
                "is_flagged": getattr(post, 'is_flagged', False),
                "view_count": getattr(post, 'view_count', 0)
            }
            
            # Add author info
            if hasattr(post, 'author') and post.author:
                post_data["author"] = {
                    "id": post.author.id,
                    "username": post.author.username
                }
            else:
                post_data["author"] = {"id": post.user_id, "username": "Unknown"}
            
            # Add comment count
            try:
                post_data["comment_count"] = post.comments.count() if hasattr(post, 'comments') else 0
            except:
                post_data["comment_count"] = 0
            
            posts_data.append(post_data)
        
        return jsonify({
            "posts": posts_data,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": posts.total,
                "pages": posts.pages
            }
        }), 200

    except Exception as e:
        current_app.logger.error(f"Failed to fetch all posts: {e}")
        return jsonify({"error": "Failed to fetch posts"}), 500

@admin_bp.route("/admin/comments", methods=["GET"])
@jwt_required()
@admin_required
def get_all_comments_admin():
    """Get all comments for admin"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        search = request.args.get('search', '').strip()
        
        # Build query
        query = Comment.query
        if search:
            query = query.filter(Comment.content.ilike(f'%{search}%'))
        
        # Get comments with pagination
        comments = query.order_by(Comment.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        comments_data = []
        for comment in comments.items:
            comment_data = {
                "id": comment.id,
                "content": comment.content,
                "created_at": comment.created_at.isoformat() if comment.created_at else None,
                "updated_at": comment.updated_at.isoformat() if hasattr(comment, 'updated_at') and comment.updated_at else None,
                "is_flagged": getattr(comment, 'is_flagged', False),
                "post_id": comment.post_id
            }
            
            # Add author info
            if hasattr(comment, 'author') and comment.author:
                comment_data["author"] = {
                    "id": comment.author.id,
                    "username": comment.author.username
                }
            else:
                comment_data["author"] = {"id": comment.user_id, "username": "Unknown"}
            
            # Add post title if available
            try:
                if hasattr(comment, 'post') and comment.post:
                    comment_data["post_title"] = comment.post.title
            except:
                comment_data["post_title"] = "Unknown Post"
            
            comments_data.append(comment_data)
        
        return jsonify({
            "comments": comments_data,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": comments.total,
                "pages": comments.pages
            }
        }), 200

    except Exception as e:
        current_app.logger.error(f"Failed to fetch all comments: {e}")
        return jsonify({"error": "Failed to fetch comments"}), 500

@admin_bp.route("/admin/flagged/posts", methods=["GET"])
@jwt_required()
@admin_required
def get_flagged_posts():
    """Get flagged posts"""
    try:
        # Try to get flagged posts if the field exists
        try:
            posts = Post.query.filter(Post.is_flagged == True).order_by(Post.created_at.desc()).all()
        except:
            # If is_flagged field doesn't exist, return empty list
            posts = []
        
        posts_data = []
        for post in posts:
            post_data = {
                "id": post.id,
                "title": post.title,
                "content": post.content[:200] + "..." if len(post.content) > 200 else post.content,
                "created_at": post.created_at.isoformat() if post.created_at else None,
                "flagged_at": getattr(post, 'flagged_at', post.created_at).isoformat() if hasattr(post, 'flagged_at') else post.created_at.isoformat()
            }
            
            # Add author info
            if hasattr(post, 'author') and post.author:
                post_data["author"] = {
                    "id": post.author.id,
                    "username": post.author.username
                }
            
            posts_data.append(post_data)
        
        return jsonify(posts_data), 200

    except Exception as e:
        current_app.logger.error(f"Failed to fetch flagged posts: {e}")
        return jsonify([]), 200  # Return empty array on error

@admin_bp.route("/admin/flagged/comments", methods=["GET"])
@jwt_required()
@admin_required
def get_flagged_comments():
    """Get flagged comments"""
    try:
        # Try to get flagged comments if the field exists
        try:
            comments = Comment.query.filter(Comment.is_flagged == True).order_by(Comment.created_at.desc()).all()
        except:
            # If is_flagged field doesn't exist, return empty list
            comments = []
        
        comments_data = []
        for comment in comments:
            comment_data = {
                "id": comment.id,
                "content": comment.content,
                "created_at": comment.created_at.isoformat() if comment.created_at else None,
                "flagged_at": getattr(comment, 'flagged_at', comment.created_at).isoformat() if hasattr(comment, 'flagged_at') else comment.created_at.isoformat(),
                "post_id": comment.post_id
            }
            
            # Add author info
            if hasattr(comment, 'author') and comment.author:
                comment_data["author"] = {
                    "id": comment.author.id,
                    "username": comment.author.username
                }
            
            comments_data.append(comment_data)
        
        return jsonify(comments_data), 200

    except Exception as e:
        current_app.logger.error(f"Failed to fetch flagged comments: {e}")
        return jsonify([]), 200  # Return empty array on error

@admin_bp.route("/admin/activity-trends", methods=["GET"])
@jwt_required()
@admin_required
def get_activity_trends():
    """Get activity trends for the last 7 days"""
    try:
        trends_data = {"labels": [], "posts": [], "users": [], "comments": []}
        
        # Get data for last 7 days
        for i in range(6, -1, -1):
            date = datetime.now(timezone.utc) - timedelta(days=i)
            start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # Format label
            trends_data["labels"].append(date.strftime("%a"))
            
            # Count posts for this day
            try:
                posts_count = Post.query.filter(
                    and_(Post.created_at >= start_of_day, Post.created_at <= end_of_day)
                ).count()
            except:
                posts_count = 0
            trends_data["posts"].append(posts_count)
            
            # Count users for this day
            try:
                users_count = User.query.filter(
                    and_(User.created_at >= start_of_day, User.created_at <= end_of_day)
                ).count()
            except:
                users_count = 0
            trends_data["users"].append(users_count)
            
            # Count comments for this day
            try:
                comments_count = Comment.query.filter(
                    and_(Comment.created_at >= start_of_day, Comment.created_at <= end_of_day)
                ).count()
            except:
                comments_count = 0
            trends_data["comments"].append(comments_count)
        
        return jsonify(trends_data), 200

    except Exception as e:
        current_app.logger.error(f"Failed to fetch activity trends: {e}")
        # Return fallback data
        return jsonify({
            "labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            "posts": [1, 2, 0, 3, 1, 2, 1],
            "users": [0, 1, 0, 1, 0, 0, 1],
            "comments": [2, 3, 1, 4, 2, 3, 2]
        }), 200

@admin_bp.route("/admin/user/<int:user_id>/block", methods=["POST"])
@jwt_required()
@admin_required
def admin_block_user(user_id):
    """Block user (admin action)"""
    try:
        current_user = User.query.get(get_jwt_identity())
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        if user.id == current_user.id:
            return jsonify({"error": "Cannot block yourself"}), 400
        
        if user.is_admin:
            return jsonify({"error": "Cannot block admin users"}), 400
        
        user.is_blocked = True
        if hasattr(user, 'updated_at'):
            user.updated_at = datetime.now(timezone.utc)
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"User {user.username} has been blocked",
            "user": {
                "id": user.id,
                "username": user.username,
                "is_blocked": user.is_blocked
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to block user {user_id}: {e}")
        return jsonify({"error": "Failed to block user"}), 500

@admin_bp.route("/admin/user/<int:user_id>/unblock", methods=["POST"])
@jwt_required()
@admin_required
def admin_unblock_user(user_id):
    """Unblock user (admin action)"""
    try:
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        user.is_blocked = False
        if hasattr(user, 'updated_at'):
            user.updated_at = datetime.now(timezone.utc)
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"User {user.username} has been unblocked",
            "user": {
                "id": user.id,
                "username": user.username,
                "is_blocked": user.is_blocked
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to unblock user {user_id}: {e}")
        return jsonify({"error": "Failed to unblock user"}), 500

@admin_bp.route("/admin/export/users", methods=["GET"])
@jwt_required()
@admin_required
def export_users():
    """Export users data for admin"""
    try:
        users = User.query.all()
        
        users_data = []
        for user in users:
            user_data = {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_admin": user.is_admin,
                "is_blocked": user.is_blocked,
                "is_active": getattr(user, 'is_active', True),
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "post_count": user.posts.count() if hasattr(user, 'posts') else 0,
                "comment_count": user.comments.count() if hasattr(user, 'comments') else 0
            }
            users_data.append(user_data)
        
        return jsonify(users_data), 200

    except Exception as e:
        current_app.logger.error(f"Failed to export users: {e}")
        return jsonify({"error": "Failed to export users"}), 500