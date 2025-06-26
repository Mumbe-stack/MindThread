from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func, and_, or_
from datetime import datetime, timedelta
from models import db, User, Post, Comment
from functools import wraps

admin_bp = Blueprint('admin_bp', __name__, url_prefix="/api/admin")


def admin_required(f):
    """Decorator to ensure only admins can access admin endpoints"""
    @wraps(f) 
    def decorated_function(*args, **kwargs):
        current_user = User.query.get(get_jwt_identity())
        if not current_user or not current_user.is_admin:
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route("/stats", methods=["GET"])
@jwt_required()
@admin_required
def get_admin_stats():
    """Get admin dashboard statistics"""
    try:
        # Get basic counts
        total_users = User.query.count()
        total_posts = Post.query.count()
        total_comments = Comment.query.count()
        
        # Get flagged content counts
        flagged_posts = Post.query.filter_by(is_flagged=True).count()
        flagged_comments = Comment.query.filter_by(is_flagged=True).count()
        total_flagged = flagged_posts + flagged_comments
        
        # Get blocked users count
        blocked_users = User.query.filter_by(is_blocked=True).count()
        
        # Get recent activity (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        new_users_week = User.query.filter(User.created_at >= week_ago).count()
        new_posts_week = Post.query.filter(Post.created_at >= week_ago).count()
        new_comments_week = Comment.query.filter(Comment.created_at >= week_ago).count()

        return jsonify({
            "users": total_users,
            "posts": total_posts,
            "comments": total_comments,
            "flagged": total_flagged,
            "flagged_posts": flagged_posts,
            "flagged_comments": flagged_comments,
            "blocked_users": blocked_users,
            "recent_activity": {
                "new_users": new_users_week,
                "new_posts": new_posts_week,
                "new_comments": new_comments_week
            }
        }), 200

    except Exception as e:
        return jsonify({"error": f"Failed to fetch stats: {str(e)}"}), 500


@admin_bp.route("/flagged/posts", methods=["GET"])
@jwt_required()
@admin_required
def get_flagged_posts():
    """Get all flagged posts"""
    try:
        flagged_posts = Post.query.filter_by(is_flagged=True).order_by(Post.created_at.desc()).all()
        
        return jsonify([{
            "id": p.id,
            "title": p.title,
            "content": p.content[:200] + "..." if len(p.content) > 200 else p.content,
            "user_id": p.user_id,
            "created_at": p.created_at.isoformat(),
            "is_approved": p.is_approved,
            "tags": p.tags
        } for p in flagged_posts]), 200

    except Exception as e:
        return jsonify({"error": f"Failed to fetch flagged posts: {str(e)}"}), 500


@admin_bp.route("/flagged/comments", methods=["GET"])
@jwt_required()
@admin_required
def get_flagged_comments():
    """Get all flagged comments"""
    try:
        flagged_comments = Comment.query.filter_by(is_flagged=True).order_by(Comment.created_at.desc()).all()
        
        return jsonify([{
            "id": c.id,
            "content": c.content[:150] + "..." if len(c.content) > 150 else c.content,
            "post_id": c.post_id,
            "user_id": c.user_id,
            "created_at": c.created_at.isoformat(),
            "is_approved": c.is_approved
        } for c in flagged_comments]), 200

    except Exception as e:
        return jsonify({"error": f"Failed to fetch flagged comments: {str(e)}"}), 500


@admin_bp.route("/activity-trends", methods=["GET"])
@jwt_required()
@admin_required
def get_activity_trends():
    """Get weekly activity trends for charts"""
    try:
        trends_data = {"labels": [], "posts": [], "users": []}
        
        for i in range(6, -1, -1):  # Last 7 days in reverse order
            date = datetime.utcnow() - timedelta(days=i)
            start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)
            
            # Count posts and users for this day
            posts_count = Post.query.filter(
                and_(Post.created_at >= start_of_day, Post.created_at < end_of_day)
            ).count()
            
            users_count = User.query.filter(
                and_(User.created_at >= start_of_day, User.created_at < end_of_day)
            ).count()
            
            trends_data["labels"].append(date.strftime("%m/%d"))
            trends_data["posts"].append(posts_count)
            trends_data["users"].append(users_count)

        return jsonify(trends_data), 200

    except Exception as e:
        return jsonify({"error": f"Failed to fetch activity trends: {str(e)}"}), 500


@admin_bp.route("/recent-activity", methods=["GET"])
@jwt_required()
@admin_required
def get_recent_activity():
    """Get recent activity feed for admin dashboard"""
    try:
        # Get recent posts (last 10)
        recent_posts = Post.query.order_by(Post.created_at.desc()).limit(10).all()
        
        # Get recent comments (last 10)
        recent_comments = Comment.query.order_by(Comment.created_at.desc()).limit(10).all()
        
        # Get recent users (last 10)
        recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()

        return jsonify({
            "recent_posts": [{
                "id": p.id,
                "title": p.title,
                "user_id": p.user_id,
                "created_at": p.created_at.isoformat()
            } for p in recent_posts],
            "recent_comments": [{
                "id": c.id,
                "content": c.content[:100] + "..." if len(c.content) > 100 else c.content,
                "post_id": c.post_id,
                "user_id": c.user_id,
                "created_at": c.created_at.isoformat()
            } for c in recent_comments],
            "recent_users": [{
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "created_at": u.created_at.isoformat()
            } for u in recent_users]
        }), 200

    except Exception as e:
        return jsonify({"error": f"Failed to fetch recent activity: {str(e)}"}), 500


@admin_bp.route("/posts/<int:post_id>/approve", methods=["PATCH"])
@jwt_required()
@admin_required
def approve_post(post_id):
    """Approve or reject a flagged post"""
    try:
        post = Post.query.get_or_404(post_id)
        data = request.get_json()

        if "is_approved" not in data:
            return jsonify({"error": "Missing 'is_approved' field"}), 400

        post.is_approved = bool(data["is_approved"])
        post.is_flagged = False  # Clear flag when processed
        db.session.commit()

        status = "approved" if post.is_approved else "rejected"
        return jsonify({
            "success": True,
            "message": f"Post {status} successfully"
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to process post: {str(e)}"}), 500


@admin_bp.route("/comments/<int:comment_id>/approve", methods=["PATCH"])
@jwt_required()
@admin_required
def approve_comment(comment_id):
    """Approve or reject a flagged comment"""
    try:
        comment = Comment.query.get_or_404(comment_id)
        data = request.get_json()

        if "is_approved" not in data:
            return jsonify({"error": "Missing 'is_approved' field"}), 400

        comment.is_approved = bool(data["is_approved"])
        comment.is_flagged = False  # Clear flag when processed
        db.session.commit()

        status = "approved" if comment.is_approved else "rejected"
        return jsonify({
            "success": True,
            "message": f"Comment {status} successfully"
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to process comment: {str(e)}"}), 500


@admin_bp.route("/posts/<int:post_id>/flag", methods=["PATCH"])
@jwt_required()
@admin_required
def flag_post(post_id):
    """Flag a post for review"""
    try:
        post = Post.query.get_or_404(post_id)
        post.is_flagged = True
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Post flagged for review"
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to flag post: {str(e)}"}), 500


@admin_bp.route("/comments/<int:comment_id>/flag", methods=["PATCH"])
@jwt_required()
@admin_required
def flag_comment(comment_id):
    """Flag a comment for review"""
    try:
        comment = Comment.query.get_or_404(comment_id)
        comment.is_flagged = True
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Comment flagged for review"
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to flag comment: {str(e)}"}), 500


@admin_bp.route("/users/search", methods=["GET"])
@jwt_required()
@admin_required
def search_users():
    """Search users by username or email"""
    try:
        query = request.args.get('q', '').strip()
        if not query:
            return jsonify([]), 200

        users = User.query.filter(
            or_(
                User.username.ilike(f'%{query}%'),
                User.email.ilike(f'%{query}%')
            )
        ).limit(20).all()

        return jsonify([{
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "is_admin": u.is_admin,
            "is_blocked": u.is_blocked,
            "created_at": u.created_at.isoformat(),
            "post_count": len(u.posts),
            "comment_count": len(u.comments)
        } for u in users]), 200

    except Exception as e:
        return jsonify({"error": f"Search failed: {str(e)}"}), 500


@admin_bp.route("/content-stats", methods=["GET"])
@jwt_required()
@admin_required
def get_content_stats():
    """Get detailed content statistics"""
    try:
        # Post statistics
        total_posts = Post.query.count()
        approved_posts = Post.query.filter_by(is_approved=True).count()
        flagged_posts = Post.query.filter_by(is_flagged=True).count()
        
        # Comment statistics
        total_comments = Comment.query.count()
        approved_comments = Comment.query.filter_by(is_approved=True).count()
        flagged_comments = Comment.query.filter_by(is_flagged=True).count()
        
        # User statistics
        total_users = User.query.count()
        admin_users = User.query.filter_by(is_admin=True).count()
        blocked_users = User.query.filter_by(is_blocked=True).count()
        active_users = total_users - blocked_users

        # Top contributors (users with most posts)
        try:
            top_posters = db.session.query(
                User.id, User.username, func.count(Post.id).label('post_count')
            ).join(Post).group_by(User.id).order_by(func.count(Post.id).desc()).limit(5).all()
        except:
            top_posters = []

        return jsonify({
            "posts": {
                "total": total_posts,
                "approved": approved_posts,
                "flagged": flagged_posts,
                "pending": total_posts - approved_posts
            },
            "comments": {
                "total": total_comments,
                "approved": approved_comments,
                "flagged": flagged_comments,
                "pending": total_comments - approved_comments
            },
            "users": {
                "total": total_users,
                "active": active_users,
                "blocked": blocked_users,
                "admins": admin_users
            },
            "top_contributors": [{
                "id": user_id,
                "username": username,
                "post_count": post_count
            } for user_id, username, post_count in top_posters]
        }), 200

    except Exception as e:
        return jsonify({"error": f"Failed to fetch content stats: {str(e)}"}), 500


# ✅ ADDITIONAL ENDPOINTS THAT WERE MISSING

@admin_bp.route("/users/<int:user_id>/delete", methods=["DELETE"])
@jwt_required()
@admin_required
def delete_user(user_id):
    """Delete a user - Admin only"""
    try:
        current_user = User.query.get(get_jwt_identity())
        user_to_delete = User.query.get_or_404(user_id)
        
        # Prevent self-deletion
        if current_user.id == user_id:
            return jsonify({"error": "Cannot delete your own account"}), 400
        
        username = user_to_delete.username
        db.session.delete(user_to_delete)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"User '{username}' deleted successfully"
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to delete user: {str(e)}"}), 500


@admin_bp.route("/posts/<int:post_id>/delete", methods=["DELETE"])
@jwt_required()
@admin_required
def delete_post(post_id):
    """Delete a post - Admin only"""
    try:
        post = Post.query.get_or_404(post_id)
        title = post.title
        
        db.session.delete(post)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"Post '{title}' deleted successfully"
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to delete post: {str(e)}"}), 500


@admin_bp.route("/comments/<int:comment_id>/delete", methods=["DELETE"])
@jwt_required()
@admin_required
def delete_comment(comment_id):
    """Delete a comment - Admin only"""
    try:
        comment = Comment.query.get_or_404(comment_id)
        
        db.session.delete(comment)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Comment deleted successfully"
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to delete comment: {str(e)}"}), 500


@admin_bp.route("/users/<int:user_id>/toggle-admin", methods=["PATCH"])
@jwt_required()
@admin_required
def toggle_user_admin(user_id):
    """Toggle admin status for a user"""
    try:
        current_user = User.query.get(get_jwt_identity())
        user = User.query.get_or_404(user_id)
        
        # Prevent self-modification
        if current_user.id == user_id:
            return jsonify({"error": "Cannot modify your own admin status"}), 400
        
        user.is_admin = not user.is_admin
        db.session.commit()
        
        status = "promoted to admin" if user.is_admin else "removed from admin"
        return jsonify({
            "success": True,
            "message": f"User '{user.username}' {status}",
            "is_admin": user.is_admin
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to update user: {str(e)}"}), 500


@admin_bp.route("/users/<int:user_id>/toggle-block", methods=["PATCH"])
@jwt_required()
@admin_required
def toggle_user_block(user_id):
    """Toggle block status for a user"""
    try:
        current_user = User.query.get(get_jwt_identity())
        user = User.query.get_or_404(user_id)
        
        # Prevent self-blocking
        if current_user.id == user_id:
            return jsonify({"error": "Cannot block your own account"}), 400
        
        user.is_blocked = not user.is_blocked
        db.session.commit()
        
        status = "blocked" if user.is_blocked else "unblocked"
        return jsonify({
            "success": True,
            "message": f"User '{user.username}' {status}",
            "is_blocked": user.is_blocked
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to update user: {str(e)}"}), 500


@admin_bp.route("/dashboard/overview", methods=["GET"])
@jwt_required()
@admin_required
def get_dashboard_overview():
    """Get comprehensive dashboard overview"""
    try:
        # Get all statistics in one endpoint
        total_users = User.query.count()
        total_posts = Post.query.count()
        total_comments = Comment.query.count()
        
        active_users = User.query.filter_by(is_blocked=False).count()
        blocked_users = User.query.filter_by(is_blocked=True).count()
        admin_users = User.query.filter_by(is_admin=True).count()
        
        approved_posts = Post.query.filter_by(is_approved=True).count()
        flagged_posts = Post.query.filter_by(is_flagged=True).count()
        pending_posts = total_posts - approved_posts
        
        approved_comments = Comment.query.filter_by(is_approved=True).count()
        flagged_comments = Comment.query.filter_by(is_flagged=True).count()
        pending_comments = total_comments - approved_comments
        
        # Recent activity (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_users = User.query.filter(User.created_at >= yesterday).count()
        recent_posts = Post.query.filter(Post.created_at >= yesterday).count()
        recent_comments = Comment.query.filter(Comment.created_at >= yesterday).count()

        return jsonify({
            "overview": {
                "users": {
                    "total": total_users,
                    "active": active_users,
                    "blocked": blocked_users,
                    "admins": admin_users,
                    "recent": recent_users
                },
                "posts": {
                    "total": total_posts,
                    "approved": approved_posts,
                    "flagged": flagged_posts,
                    "pending": pending_posts,
                    "recent": recent_posts
                },
                "comments": {
                    "total": total_comments,
                    "approved": approved_comments,
                    "flagged": flagged_comments,
                    "pending": pending_comments,
                    "recent": recent_comments
                }
            }
        }), 200

    except Exception as e:
        return jsonify({"error": f"Failed to fetch overview: {str(e)}"}), 500


@admin_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for admin services"""
    return jsonify({
        "status": "healthy",
        "service": "admin",
        "timestamp": datetime.utcnow().isoformat()
    }), 200