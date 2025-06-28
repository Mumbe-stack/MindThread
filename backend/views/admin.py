from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, Post, Comment, Vote, Like
from datetime import datetime, timezone, timedelta
from sqlalchemy import func, desc
from functools import wraps
import logging

def admin_required(fn):
    """Admin decorator - ensures only admin users can access endpoints"""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            user_id = get_jwt_identity()
            user = User.query.get(user_id)
            if not user or not user.is_admin:
                return jsonify({"error": "Admin privileges required"}), 403
            return fn(*args, **kwargs)
        except Exception as e:
            return jsonify({"error": "Authorization failed"}), 500
    return wrapper

def paginate_query(query, page=1, per_page=20, max_per_page=100):
    """Simple pagination function"""
    try:
        page = max(1, page)
        per_page = min(max(1, per_page), max_per_page)
        
        total = query.count()
        items = query.offset((page - 1) * per_page).limit(per_page).all()
        
        return {
            "items": items,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page,
                "has_next": (page * per_page) < total,
                "has_prev": page > 1,
                "next_page": page + 1 if (page * per_page) < total else None,
                "prev_page": page - 1 if page > 1 else None
            }
        }
    except Exception as e:
        return {
            "items": [],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": 0,
                "pages": 0,
                "has_next": False,
                "has_prev": False,
                "next_page": None,
                "prev_page": None
            }
        }

logger = logging.getLogger(__name__)

# Create Blueprint
admin_bp = Blueprint('admin', __name__)

@admin_bp.route("/admin/stats", methods=["GET"])
@jwt_required()
@admin_required
def get_admin_stats():
    """Get comprehensive admin statistics"""
    try:
        # Basic counts
        total_users = User.query.count()
        active_users = User.query.filter_by(is_active=True).count() if hasattr(User, 'is_active') else total_users
        blocked_users = User.query.filter_by(is_blocked=True).count()
        admin_users = User.query.filter_by(is_admin=True).count()
        
        total_posts = Post.query.count()
        approved_posts = Post.query.filter_by(is_approved=True).count()
        flagged_posts = Post.query.filter_by(is_flagged=True).count()
        
        total_comments = Comment.query.count()
        approved_comments = Comment.query.filter_by(is_approved=True).count()
        flagged_comments = Comment.query.filter_by(is_flagged=True).count()
        
        total_votes = Vote.query.count()
        total_likes = Like.query.count()
        
        # Recent activity (last 30 days)
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        recent_users = User.query.filter(User.created_at >= thirty_days_ago).count()
        recent_posts = Post.query.filter(Post.created_at >= thirty_days_ago).count()
        recent_comments = Comment.query.filter(Comment.created_at >= thirty_days_ago).count()
        
        stats = {
            "users": total_users,
            "active_users": active_users,
            "blocked_users": blocked_users,
            "admin_users": admin_users,
            "posts": total_posts,
            "approved_posts": approved_posts,
            "flagged_posts": flagged_posts,
            "comments": total_comments,
            "approved_comments": approved_comments,
            "flagged_comments": flagged_comments,
            "flagged": flagged_posts + flagged_comments,
            "total_votes": total_votes,
            "total_likes": total_likes,
            "recent_activity": {
                "users": recent_users,
                "posts": recent_posts,
                "comments": recent_comments
            }
        }
        
        return jsonify(stats), 200
        
    except Exception as e:
        logger.error(f"Error fetching admin stats: {e}")
        return jsonify({"error": "Failed to fetch statistics"}), 500

@admin_bp.route("/admin/activity-trends", methods=["GET"])
@jwt_required()
@admin_required
def get_activity_trends():
    """Get activity trends for charts"""
    try:
        # Get data for last 7 days
        today = datetime.now(timezone.utc).date()
        week_ago = today - timedelta(days=6)
        
        # Daily post counts
        daily_posts = []
        daily_users = []
        labels = []
        
        for i in range(7):
            day = week_ago + timedelta(days=i)
            day_start = datetime.combine(day, datetime.min.time()).replace(tzinfo=timezone.utc)
            day_end = datetime.combine(day, datetime.max.time()).replace(tzinfo=timezone.utc)
            
            posts_count = Post.query.filter(
                Post.created_at >= day_start,
                Post.created_at <= day_end
            ).count()
            
            users_count = User.query.filter(
                User.created_at >= day_start,
                User.created_at <= day_end
            ).count()
            
            daily_posts.append(posts_count)
            daily_users.append(users_count)
            labels.append(day.strftime('%a'))
        
        return jsonify({
            "labels": labels,
            "posts": daily_posts,
            "users": daily_users
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching activity trends: {e}")
        return jsonify({
            "labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            "posts": [0, 0, 0, 0, 0, 0, 0],
            "users": [0, 0, 0, 0, 0, 0, 0]
        }), 200

@admin_bp.route("/admin/flagged/posts", methods=["GET"])
@jwt_required()
@admin_required
def get_flagged_posts():
    """Get all flagged posts"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        
        query = Post.query.filter_by(is_flagged=True).order_by(desc(Post.updated_at))
        
        result = paginate_query(query, page, per_page)
        
        posts_data = []
        for post in result['items']:
            author = User.query.get(post.user_id)
            posts_data.append({
                "id": post.id,
                "title": post.title,
                "content": post.content[:200] + "..." if len(post.content) > 200 else post.content,
                "author": {
                    "id": author.id,
                    "username": author.username
                } if author else {"id": None, "username": "Unknown"},
                "created_at": post.created_at.isoformat() if post.created_at else None,
                "updated_at": post.updated_at.isoformat() if post.updated_at else None,
                "is_approved": post.is_approved,
                "is_flagged": post.is_flagged
            })
        
        return jsonify({
            "posts": posts_data,
            "pagination": result['pagination']
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching flagged posts: {e}")
        return jsonify({"error": "Failed to fetch flagged posts"}), 500

@admin_bp.route("/admin/flagged/comments", methods=["GET"])
@jwt_required()
@admin_required
def get_flagged_comments():
    """Get all flagged comments"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        
        query = Comment.query.filter_by(is_flagged=True).order_by(desc(Comment.updated_at))
        
        result = paginate_query(query, page, per_page)
        
        comments_data = []
        for comment in result['items']:
            author = User.query.get(comment.user_id)
            post = Post.query.get(comment.post_id)
            comments_data.append({
                "id": comment.id,
                "content": comment.content,
                "post_id": comment.post_id,
                "post_title": post.title if post else "Unknown Post",
                "author": {
                    "id": author.id,
                    "username": author.username
                } if author else {"id": None, "username": "Unknown"},
                "created_at": comment.created_at.isoformat() if comment.created_at else None,
                "updated_at": comment.updated_at.isoformat() if comment.updated_at else None,
                "is_approved": comment.is_approved,
                "is_flagged": comment.is_flagged
            })
        
        return jsonify({
            "comments": comments_data,
            "pagination": result['pagination']
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching flagged comments: {e}")
        return jsonify({"error": "Failed to fetch flagged comments"}), 500

@admin_bp.route("/admin/users/search", methods=["GET"])
@jwt_required()
@admin_required
def search_users_admin():
    """Search users for admin"""
    try:
        query = request.args.get('q', '').strip()
        if not query:
            return jsonify({"error": "Search query required"}), 400
        
        users = User.query.filter(
            db.or_(
                User.username.ilike(f'%{query}%'),
                User.email.ilike(f'%{query}%')
            )
        ).limit(50).all()
        
        users_data = []
        for user in users:
            users_data.append({
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_admin": user.is_admin,
                "is_blocked": user.is_blocked,
                "is_active": getattr(user, 'is_active', True),
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "post_count": user.posts.count() if hasattr(user, 'posts') else 0,
                "comment_count": user.comments.count() if hasattr(user, 'comments') else 0
            })
        
        return jsonify({
            "users": users_data,
            "query": query,
            "count": len(users_data)
        }), 200
        
    except Exception as e:
        logger.error(f"Error searching users: {e}")
        return jsonify({"error": "Failed to search users"}), 500

@admin_bp.route("/admin/content/pending", methods=["GET"])
@jwt_required()
@admin_required
def get_pending_content():
    """Get content pending approval"""
    try:
        pending_posts = Post.query.filter_by(is_approved=False).order_by(desc(Post.created_at)).limit(10).all()
        pending_comments = Comment.query.filter_by(is_approved=False).order_by(desc(Comment.created_at)).limit(10).all()
        
        posts_data = []
        for post in pending_posts:
            author = User.query.get(post.user_id)
            posts_data.append({
                "id": post.id,
                "title": post.title,
                "content": post.content[:150] + "..." if len(post.content) > 150 else post.content,
                "author": {
                    "id": author.id,
                    "username": author.username
                } if author else {"id": None, "username": "Unknown"},
                "created_at": post.created_at.isoformat() if post.created_at else None
            })
        
        comments_data = []
        for comment in pending_comments:
            author = User.query.get(comment.user_id)
            post = Post.query.get(comment.post_id)
            comments_data.append({
                "id": comment.id,
                "content": comment.content,
                "post_title": post.title if post else "Unknown Post",
                "author": {
                    "id": author.id,
                    "username": author.username
                } if author else {"id": None, "username": "Unknown"},
                "created_at": comment.created_at.isoformat() if comment.created_at else None
            })
        
        return jsonify({
            "pending_posts": posts_data,
            "pending_comments": comments_data
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching pending content: {e}")
        return jsonify({"error": "Failed to fetch pending content"}), 500

@admin_bp.route("/admin/reports", methods=["GET"])
@jwt_required()
@admin_required
def generate_reports():
    """Generate various admin reports"""
    try:
        report_type = request.args.get('type', 'summary')
        
        if report_type == 'user_activity':
            # User activity report
            thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
            
            active_users = db.session.query(
                User.id,
                User.username,
                func.count(Post.id).label('post_count'),
                func.count(Comment.id).label('comment_count')
            ).outerjoin(Post).outerjoin(Comment).filter(
                db.or_(
                    Post.created_at >= thirty_days_ago,
                    Comment.created_at >= thirty_days_ago
                )
            ).group_by(User.id).limit(20).all()
            
            report_data = [
                {
                    "user_id": user.id,
                    "username": user.username,
                    "posts": user.post_count,
                    "comments": user.comment_count
                }
                for user in active_users
            ]
            
        elif report_type == 'content_stats':
            # Content statistics report
            report_data = {
                "posts_by_status": {
                    "approved": Post.query.filter_by(is_approved=True).count(),
                    "pending": Post.query.filter_by(is_approved=False).count(),
                    "flagged": Post.query.filter_by(is_flagged=True).count()
                },
                "comments_by_status": {
                    "approved": Comment.query.filter_by(is_approved=True).count(),
                    "pending": Comment.query.filter_by(is_approved=False).count(),
                    "flagged": Comment.query.filter_by(is_flagged=True).count()
                }
            }
            
        else:
            # Default summary report
            report_data = {
                "total_users": User.query.count(),
                "total_posts": Post.query.count(),
                "total_comments": Comment.query.count(),
                "flagged_content": Post.query.filter_by(is_flagged=True).count() + Comment.query.filter_by(is_flagged=True).count()
            }
        
        return jsonify({
            "report_type": report_type,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "data": report_data
        }), 200
        
    except Exception as e:
        logger.error(f"Error generating reports: {e}")
        return jsonify({"error": "Failed to generate report"}), 500

# Bulk actions
@admin_bp.route("/admin/bulk/approve", methods=["POST"])
@jwt_required()
@admin_required
def bulk_approve_content():
    """Bulk approve posts or comments"""
    try:
        data = request.get_json()
        content_type = data.get('type')  # 'posts' or 'comments'
        ids = data.get('ids', [])
        
        if not content_type or not ids:
            return jsonify({"error": "Content type and IDs required"}), 400
        
        updated_count = 0
        
        if content_type == 'posts':
            Post.query.filter(Post.id.in_(ids)).update(
                {"is_approved": True, "updated_at": datetime.now(timezone.utc)},
                synchronize_session=False
            )
            updated_count = len(ids)
        elif content_type == 'comments':
            Comment.query.filter(Comment.id.in_(ids)).update(
                {"is_approved": True, "updated_at": datetime.now(timezone.utc)},
                synchronize_session=False
            )
            updated_count = len(ids)
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"Approved {updated_count} {content_type}",
            "updated_count": updated_count
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in bulk approve: {e}")
        return jsonify({"error": "Failed to bulk approve content"}), 500

@admin_bp.route("/admin/bulk/delete", methods=["POST"])
@jwt_required()
@admin_required
def bulk_delete_content():
    """Bulk delete posts or comments"""
    try:
        data = request.get_json()
        content_type = data.get('type')
        ids = data.get('ids', [])
        
        if not content_type or not ids:
            return jsonify({"error": "Content type and IDs required"}), 400
        
        deleted_count = 0
        
        if content_type == 'posts':
            deleted_count = Post.query.filter(Post.id.in_(ids)).count()
            Post.query.filter(Post.id.in_(ids)).delete(synchronize_session=False)
        elif content_type == 'comments':
            deleted_count = Comment.query.filter(Comment.id.in_(ids)).count()
            Comment.query.filter(Comment.id.in_(ids)).delete(synchronize_session=False)
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"Deleted {deleted_count} {content_type}",
            "deleted_count": deleted_count
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in bulk delete: {e}")
        return jsonify({"error": "Failed to bulk delete content"}), 500