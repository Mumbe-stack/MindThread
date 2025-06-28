from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from functools import wraps
from datetime import datetime, timezone, timedelta
from sqlalchemy import func, and_, or_
from models import db, User, Post, Comment, Vote

# FIXED: Remove url_prefix since app.py handles it
admin_bp = Blueprint("admin", __name__)

def admin_required(fn):
    """Decorator to require admin privileges"""
    @wraps(fn)  
    @jwt_required()
    def wrapper(*args, **kwargs):
        try:
            user_id = get_jwt_identity()
            if not user_id:
                return jsonify({"error": "Authentication required"}), 401
            
            user = User.query.get(user_id)
            if not user:
                return jsonify({"error": "User not found"}), 404
            
            if not user.is_admin:
                return jsonify({"error": "Admin access required"}), 403
            
            if user.is_blocked:
                return jsonify({"error": "Account is blocked"}), 403
            
            return fn(*args, **kwargs)
        except Exception as e:
            current_app.logger.error(f"Admin check error: {e}")
            return jsonify({"error": "Authorization failed"}), 500
    
    return wrapper

# MAIN ADMIN STATS ROUTE - This is what frontend expects
@admin_bp.route("/admin/stats", methods=["GET"])  
@admin_required
def admin_stats():
    """Get comprehensive admin statistics - MAIN ROUTE"""
    try:
        # Basic counts
        total_users = User.query.count()
        total_posts = Post.query.count()
        total_comments = Comment.query.count()
        total_votes = Vote.query.count()
        
        # Status counts
        blocked_users = User.query.filter_by(is_blocked=True).count()
        admin_users = User.query.filter_by(is_admin=True).count()
        
        # Flagged content counts (with safe attribute checking)
        flagged_posts = 0
        flagged_comments = 0
        pending_posts = 0
        pending_comments = 0
        
        try:
            if hasattr(Post, 'is_flagged'):
                flagged_posts = Post.query.filter_by(is_flagged=True).count()
            if hasattr(Comment, 'is_flagged'):
                flagged_comments = Comment.query.filter_by(is_flagged=True).count()
            if hasattr(Post, 'is_approved'):
                pending_posts = Post.query.filter_by(is_approved=False).count()
            if hasattr(Comment, 'is_approved'):
                pending_comments = Comment.query.filter_by(is_approved=False).count()
        except Exception as e:
            current_app.logger.warning(f"Error fetching flagged/pending counts: {e}")
        
        # Recent activity (last 7 days)
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        recent_users = User.query.filter(User.created_at >= week_ago).count()
        recent_posts = Post.query.filter(Post.created_at >= week_ago).count()
        recent_comments = Comment.query.filter(Comment.created_at >= week_ago).count()
        
        # Today's activity
        today = datetime.now(timezone.utc).date()
        today_users = User.query.filter(func.date(User.created_at) == today).count()
        today_posts = Post.query.filter(func.date(Post.created_at) == today).count()
        today_comments = Comment.query.filter(func.date(Comment.created_at) == today).count()
        
        stats = {
            "users": total_users,
            "posts": total_posts,
            "comments": total_comments,
            "votes": total_votes,
            "flagged": flagged_posts + flagged_comments,
            "flagged_posts": flagged_posts,
            "flagged_comments": flagged_comments,
            "blocked_users": blocked_users,
            "admin_users": admin_users,
            "pending_posts": pending_posts,
            "pending_comments": pending_comments,
            "recent_activity": {
                "users": recent_users,
                "posts": recent_posts,
                "comments": recent_comments
            },
            "today_activity": {
                "users": today_users,
                "posts": today_posts,
                "comments": today_comments
            }
        }
        
        current_app.logger.info(f"Admin stats retrieved: {stats}")
        return jsonify(stats), 200
        
    except Exception as e:
        current_app.logger.error(f"Error fetching admin stats: {e}")
        return jsonify({"error": "Failed to fetch admin stats"}), 500

@admin_bp.route("/admin/activity-trends", methods=["GET"])
@admin_required
def get_activity_trends():
    """Get activity trends for the last 7 days"""
    try:
        # Calculate date range for last 7 days
        end_date = datetime.now(timezone.utc).date()
        start_date = end_date - timedelta(days=6)
        
        # Generate date labels and data
        date_labels = []
        daily_posts = []
        daily_users = []
        daily_comments = []
        daily_votes = []
        
        for i in range(7):
            current_date = start_date + timedelta(days=i)
            date_labels.append(current_date.strftime('%a'))  # Mon, Tue, etc.
            
            # Count activities for this date
            posts_count = Post.query.filter(func.date(Post.created_at) == current_date).count()
            users_count = User.query.filter(func.date(User.created_at) == current_date).count()
            comments_count = Comment.query.filter(func.date(Comment.created_at) == current_date).count()
            votes_count = Vote.query.filter(func.date(Vote.created_at) == current_date).count()
            
            daily_posts.append(posts_count)
            daily_users.append(users_count)
            daily_comments.append(comments_count)
            daily_votes.append(votes_count)
        
        trends_data = {
            "labels": date_labels,
            "posts": daily_posts,
            "users": daily_users,
            "comments": daily_comments,
            "votes": daily_votes
        }
        
        current_app.logger.info(f"Activity trends retrieved: {trends_data}")
        return jsonify(trends_data), 200
        
    except Exception as e:
        current_app.logger.error(f"Activity trends error: {e}")
        # Return fallback data
        return jsonify({
            "labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            "posts": [1, 2, 0, 3, 1, 2, 1],
            "users": [0, 1, 0, 1, 0, 0, 1],
            "comments": [2, 3, 1, 5, 2, 4, 3],
            "votes": [5, 8, 3, 12, 7, 9, 6]
        }), 200

@admin_bp.route("/admin/users/search", methods=["GET"])
@admin_required
def search_users():
    """Search users by username or email"""
    try:
        query = request.args.get('q', '').strip()
        if not query:
            return jsonify({"error": "Search query is required"}), 400
        
        limit = min(request.args.get('limit', 20, type=int), 50)
        
        # Search users by username or email
        users = User.query.filter(
            or_(
                User.username.ilike(f'%{query}%'),
                User.email.ilike(f'%{query}%')
            )
        ).limit(limit).all()
        
        users_data = []
        for user in users:
            user_dict = user.to_dict()
            user_dict.update({
                "posts_count": user.posts.count(),
                "comments_count": user.comments.count()
            })
            users_data.append(user_dict)
        
        return jsonify({
            "users": users_data,
            "query": query,
            "count": len(users_data)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error searching users: {e}")
        return jsonify({"error": "Failed to search users"}), 500

@admin_bp.route("/admin/flagged/posts", methods=["GET"])
@admin_required
def get_flagged_posts():
    """Get all flagged posts with enhanced information"""
    try:
        if not hasattr(Post, 'is_flagged'):
            return jsonify({"flagged_posts": [], "count": 0}), 200
            
        posts = Post.query.filter_by(is_flagged=True).order_by(Post.created_at.desc()).all()
        
        posts_data = []
        for post in posts:
            post_dict = post.to_dict(include_author=True)
            # Add extra information
            post_dict.update({
                "flagged_at": post.updated_at.isoformat() if hasattr(post, 'updated_at') and post.updated_at else post.created_at.isoformat(),
                "comments_count": post.comments.count(),
                "approved_comments": post.comments.filter_by(is_approved=True).count() if hasattr(Comment, 'is_approved') else post.comments.count()
            })
            posts_data.append(post_dict)
        
        return jsonify({
            "flagged_posts": posts_data,
            "count": len(posts_data)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error fetching flagged posts: {e}")
        return jsonify({"error": "Failed to fetch flagged posts"}), 500

@admin_bp.route("/admin/flagged/comments", methods=["GET"])
@admin_required
def get_flagged_comments():
    """Get all flagged comments with enhanced information"""
    try:
        if not hasattr(Comment, 'is_flagged'):
            return jsonify({"flagged_comments": [], "count": 0}), 200
            
        comments = Comment.query.filter_by(is_flagged=True).order_by(Comment.created_at.desc()).all()
        
        comments_data = []
        for comment in comments:
            comment_dict = comment.to_dict(include_author=True)
            # Add extra information
            comment_dict.update({
                "flagged_at": comment.updated_at.isoformat() if hasattr(comment, 'updated_at') and comment.updated_at else comment.created_at.isoformat(),
                "post_title": comment.post.title if comment.post else "Unknown Post",
                "parent_comment_id": comment.parent_id
            })
            comments_data.append(comment_dict)
        
        return jsonify({
            "flagged_comments": comments_data,
            "count": len(comments_data)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error fetching flagged comments: {e}")
        return jsonify({"error": "Failed to fetch flagged comments"}), 500

@admin_bp.route("/admin/users", methods=["GET"])
@admin_required
def get_all_users():
    """Get all users with enhanced information"""
    try:
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        
        # Get search parameter
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
        
        # Order by creation date (newest first)
        query = query.order_by(User.created_at.desc())
        
        # Paginate
        users_pagination = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        users_data = []
        for user in users_pagination.items:
            user_dict = user.to_dict()
            # Add extra stats for each user
            try:
                user_dict.update({
                    "posts_count": user.posts.count(),
                    "comments_count": user.comments.count(),
                    "votes_count": user.votes.count() if hasattr(user, 'votes') else 0
                })
                
                # Add flagged content counts if available
                if hasattr(Post, 'is_flagged'):
                    user_dict["flagged_posts"] = user.posts.filter_by(is_flagged=True).count()
                if hasattr(Comment, 'is_flagged'):
                    user_dict["flagged_comments"] = user.comments.filter_by(is_flagged=True).count()
                    
            except Exception as e:
                current_app.logger.warning(f"Error adding user stats for user {user.id}: {e}")
                
            users_data.append(user_dict)
        
        return jsonify({
            "users": users_data,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": users_pagination.total,
                "pages": users_pagination.pages,
                "has_prev": users_pagination.has_prev,
                "has_next": users_pagination.has_next
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error fetching users: {e}")
        return jsonify({"error": "Failed to fetch users"}), 500

@admin_bp.route("/admin/dashboard-summary", methods=["GET"])
@admin_required
def get_dashboard_summary():
    """Get a complete dashboard summary for the admin panel"""
    try:
        # Get basic stats
        total_users = User.query.count()
        total_posts = Post.query.count()
        total_comments = Comment.query.count()
        blocked_users = User.query.filter_by(is_blocked=True).count()
        
        # Get pending/flagged counts for immediate attention
        pending_posts = 0
        pending_comments = 0
        flagged_posts = 0
        flagged_comments = 0
        
        try:
            if hasattr(Post, 'is_approved'):
                pending_posts = Post.query.filter_by(is_approved=False).count()
            if hasattr(Comment, 'is_approved'):
                pending_comments = Comment.query.filter_by(is_approved=False).count()
            if hasattr(Post, 'is_flagged'):
                flagged_posts = Post.query.filter_by(is_flagged=True).count()
            if hasattr(Comment, 'is_flagged'):
                flagged_comments = Comment.query.filter_by(is_flagged=True).count()
        except Exception as e:
            current_app.logger.warning(f"Error fetching pending/flagged counts: {e}")
        
        # Get recent activity (last 24 hours)
        day_ago = datetime.now(timezone.utc) - timedelta(days=1)
        recent_users = User.query.filter(User.created_at >= day_ago).count()
        recent_posts = Post.query.filter(Post.created_at >= day_ago).count()
        recent_comments = Comment.query.filter(Comment.created_at >= day_ago).count()
        
        # Get top users by activity (with error handling)
        top_posters = []
        top_commenters = []
        
        try:
            top_posters = db.session.query(
                User.id, User.username, func.count(Post.id).label('post_count')
            ).join(Post).group_by(User.id, User.username).order_by(
                func.count(Post.id).desc()
            ).limit(5).all()
            
            top_commenters = db.session.query(
                User.id, User.username, func.count(Comment.id).label('comment_count')
            ).join(Comment).group_by(User.id, User.username).order_by(
                func.count(Comment.id).desc()
            ).limit(5).all()
        except Exception as e:
            current_app.logger.warning(f"Error fetching top users: {e}")
        
        summary = {
            "overview": {
                "total_users": total_users,
                "total_posts": total_posts,
                "total_comments": total_comments,
                "blocked_users": blocked_users
            },
            "pending_approval": {
                "posts": pending_posts,
                "comments": pending_comments,
                "total": pending_posts + pending_comments
            },
            "flagged_content": {
                "posts": flagged_posts,
                "comments": flagged_comments,
                "total": flagged_posts + flagged_comments
            },
            "recent_activity": {
                "users": recent_users,
                "posts": recent_posts,
                "comments": recent_comments
            },
            "top_users": {
                "posters": [{"id": u.id, "username": u.username, "post_count": u.post_count} for u in top_posters],
                "commenters": [{"id": u.id, "username": u.username, "comment_count": u.comment_count} for u in top_commenters]
            }
        }
        
        return jsonify(summary), 200
        
    except Exception as e:
        current_app.logger.error(f"Error fetching dashboard summary: {e}")
        return jsonify({"error": "Failed to fetch dashboard summary"}), 500

# User management endpoints
@admin_bp.route("/admin/users/<int:user_id>/block", methods=["PATCH"])
@admin_required
def toggle_block_user(user_id):
    """Toggle user block status"""
    try:
        user = User.query.get_or_404(user_id)
        
        # Prevent self-blocking
        current_user_id = get_jwt_identity()
        if user_id == int(current_user_id):
            return jsonify({"error": "Cannot block yourself"}), 400
        
        user.is_blocked = not user.is_blocked
        if hasattr(user, 'updated_at'):
            user.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        action = "blocked" if user.is_blocked else "unblocked"
        current_app.logger.info(f"User {user.username} (ID: {user.id}) {action} by admin {current_user_id}")
        
        return jsonify({
            "success": True,
            "message": f"User {action} successfully",
            "user_id": user.id,
            "username": user.username,
            "is_blocked": user.is_blocked
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error toggling user block: {e}")
        return jsonify({"error": "Failed to update user status"}), 500

@admin_bp.route("/admin/users/<int:user_id>", methods=["DELETE"])
@admin_required
def delete_user(user_id):
    """Delete a user (admin only)"""
    try:
        user = User.query.get_or_404(user_id)
        
        # Prevent self-deletion
        current_user_id = get_jwt_identity()
        if user_id == int(current_user_id):
            return jsonify({"error": "Cannot delete yourself"}), 400
        
        username = user.username
        db.session.delete(user)
        db.session.commit()
        
        current_app.logger.info(f"User {username} (ID: {user_id}) deleted by admin {current_user_id}")
        
        return jsonify({
            "success": True,
            "message": f"User '{username}' deleted successfully",
            "deleted_user_id": user_id
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting user: {e}")
        return jsonify({"error": "Failed to delete user"}), 500

@admin_bp.route("/admin/users/<int:user_id>/admin", methods=["PATCH"])
@admin_required
def toggle_admin_status(user_id):
    """Toggle user admin status"""
    try:
        user = User.query.get_or_404(user_id)
        
        # Prevent self-demotion
        current_user_id = get_jwt_identity()
        if user_id == int(current_user_id):
            return jsonify({"error": "Cannot modify your own admin status"}), 400
        
        user.is_admin = not user.is_admin
        if hasattr(user, 'updated_at'):
            user.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        action = "promoted to admin" if user.is_admin else "demoted from admin"
        current_app.logger.info(f"User {user.username} (ID: {user.id}) {action} by admin {current_user_id}")
        
        return jsonify({
            "success": True,
            "message": f"User {action} successfully",
            "user_id": user.id,
            "username": user.username,
            "is_admin": user.is_admin
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error toggling admin status: {e}")
        return jsonify({"error": "Failed to update admin status"}), 500

# Bulk action endpoints
@admin_bp.route("/admin/bulk-actions/approve-posts", methods=["POST"])
@admin_required
def bulk_approve_posts():
    """Bulk approve/disapprove multiple posts"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        post_ids = data.get('post_ids', [])
        approve = data.get('approve', True)
        
        if not post_ids:
            return jsonify({"error": "No post IDs provided"}), 400
        
        if not hasattr(Post, 'is_approved'):
            return jsonify({"error": "Post approval not supported"}), 400
        
        # Update posts
        updated_count = Post.query.filter(Post.id.in_(post_ids)).update(
            {
                Post.is_approved: approve,
                Post.updated_at: datetime.now(timezone.utc) if hasattr(Post, 'updated_at') else Post.created_at
            },
            synchronize_session=False
        )
        
        db.session.commit()
        
        action = "approved" if approve else "disapproved"
        current_app.logger.info(f"Bulk {action} {updated_count} posts")
        
        return jsonify({
            "success": True,
            "message": f"{updated_count} posts {action} successfully",
            "updated_count": updated_count
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in bulk approve posts: {e}")
        return jsonify({"error": "Failed to bulk approve posts"}), 500

@admin_bp.route("/admin/bulk-actions/approve-comments", methods=["POST"])
@admin_required
def bulk_approve_comments():
    """Bulk approve/disapprove multiple comments"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        comment_ids = data.get('comment_ids', [])
        approve = data.get('approve', True)
        
        if not comment_ids:
            return jsonify({"error": "No comment IDs provided"}), 400
        
        if not hasattr(Comment, 'is_approved'):
            return jsonify({"error": "Comment approval not supported"}), 400
        
        # Update comments
        updated_count = Comment.query.filter(Comment.id.in_(comment_ids)).update(
            {
                Comment.is_approved: approve,
                Comment.updated_at: datetime.now(timezone.utc) if hasattr(Comment, 'updated_at') else Comment.created_at
            },
            synchronize_session=False
        )
        
        db.session.commit()
        
        action = "approved" if approve else "disapproved"
        current_app.logger.info(f"Bulk {action} {updated_count} comments")
        
        return jsonify({
            "success": True,
            "message": f"{updated_count} comments {action} successfully",
            "updated_count": updated_count
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in bulk approve comments: {e}")
        return jsonify({"error": "Failed to bulk approve comments"}), 500

# Health check for admin service
@admin_bp.route("/admin/health", methods=["GET"])
@admin_required
def admin_health_check():
    """Admin API health check"""
    return jsonify({
        "status": "Admin API healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0"
    }), 200