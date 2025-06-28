from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from functools import wraps
from datetime import datetime, timezone, timedelta
from sqlalchemy import func, or_
from models import db, User, Post, Comment, Vote

admin_bp = Blueprint("admin", __name__)

def admin_required(fn):
    """Decorator to require admin privileges"""
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        try:
            uid = get_jwt_identity()
            if not uid:
                return jsonify({"error": "Authentication required"}), 401

            user = User.query.get(uid)
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

@admin_bp.route("/admin/stats", methods=["GET"])
@admin_required
def admin_stats():
    """Get comprehensive admin statistics"""
    try:
        # Basic totals
        total_users    = User.query.count()
        total_posts    = Post.query.count()
        total_comments = Comment.query.count()
        total_votes    = Vote.query.count()

        # Status counts
        blocked_users = User.query.filter_by(is_blocked=True).count()
        admin_users   = User.query.filter_by(is_admin=True).count()

        # Flagged/pending
        flagged_posts    = Post.query.filter_by(is_flagged=True).count()
        flagged_comments = Comment.query.filter_by(is_flagged=True).count()
        pending_posts    = Post.query.filter_by(is_approved=False).count()
        pending_comments = Comment.query.filter_by(is_approved=False).count()

        # Recent 7-day activity
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        recent_users    = User.query.filter(User.created_at >= week_ago).count()
        recent_posts    = Post.query.filter(Post.created_at >= week_ago).count()
        recent_comments = Comment.query.filter(Comment.created_at >= week_ago).count()

        # Today’s activity
        today = datetime.now(timezone.utc).date()
        today_users    = User.query.filter(func.date(User.created_at) == today).count()
        today_posts    = Post.query.filter(func.date(Post.created_at) == today).count()
        today_comments = Comment.query.filter(func.date(Comment.created_at) == today).count()

        stats = {
            "users": total_users,
            "posts": total_posts,
            "comments": total_comments,
            "votes": total_votes,
            "blocked_users": blocked_users,
            "admin_users": admin_users,
            "flagged": flagged_posts + flagged_comments,
            "flagged_posts": flagged_posts,
            "flagged_comments": flagged_comments,
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
        current_app.logger.info(f"Admin stats: {stats}")
        return jsonify(stats), 200

    except Exception as e:
        current_app.logger.error(f"Error in admin_stats: {e}")
        return jsonify({"error": "Failed to fetch admin stats"}), 500

@admin_bp.route("/admin/activity-trends", methods=["GET"])
@admin_required
def get_activity_trends():
    """Get 7-day activity trends"""
    try:
        end_date = datetime.now(timezone.utc).date()
        start_date = end_date - timedelta(days=6)
        labels = []
        posts, users, comments, votes = [], [], [], []

        for i in range(7):
            d = start_date + timedelta(days=i)
            labels.append(d.strftime('%a'))
            posts.append(Post.query.filter(func.date(Post.created_at)==d).count())
            users.append(User.query.filter(func.date(User.created_at)==d).count())
            comments.append(Comment.query.filter(func.date(Comment.created_at)==d).count())
            votes.append(Vote.query.filter(func.date(Vote.created_at)==d).count())

        data = {"labels": labels, "posts": posts, "users": users, "comments": comments, "votes": votes}
        current_app.logger.info(f"Activity trends: {data}")
        return jsonify(data), 200

    except Exception as e:
        current_app.logger.error(f"Error in get_activity_trends: {e}")
        # fallback
        return jsonify({
            "labels": ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"],
            "posts":    [0]*7,
            "users":    [0]*7,
            "comments": [0]*7,
            "votes":    [0]*7
        }), 200

@admin_bp.route("/admin/users/search", methods=["GET"])
@admin_required
def search_users():
    """Search users by username or email"""
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify({"error": "Search query is required"}), 400

    limit = min(request.args.get('limit', 20, type=int), 50)
    results = User.query.filter(
        or_(User.username.ilike(f'%{q}%'), User.email.ilike(f'%{q}%'))
    ).limit(limit).all()

    users = []
    for u in results:
        d = u.to_dict()
        d.update({
            "posts_count": u.posts.count(),
            "comments_count": u.comments.count()
        })
        users.append(d)

    return jsonify({"users": users, "count": len(users)}), 200

@admin_bp.route("/admin/flagged/posts", methods=["GET"])
@admin_required
def get_flagged_posts():
    """List flagged posts"""
    flagged = Post.query.filter_by(is_flagged=True).order_by(Post.created_at.desc()).all()
    data = []
    for p in flagged:
        d = p.to_dict(include_author=True)
        d.update({
            "flagged_at": (p.updated_at or p.created_at).isoformat(),
            "comments_count": p.comments.count(),
            "approved_comments": p.comments.filter_by(is_approved=True).count()
        })
        data.append(d)
    return jsonify({"flagged_posts": data, "count": len(data)}), 200

@admin_bp.route("/admin/flagged/comments", methods=["GET"])
@admin_required
def get_flagged_comments():
    """List flagged comments"""
    flagged = Comment.query.filter_by(is_flagged=True).order_by(Comment.created_at.desc()).all()
    data = []
    for c in flagged:
        d = c.to_dict(include_author=True)
        d.update({
            "flagged_at": (c.updated_at or c.created_at).isoformat(),
            "post_title": c.post.title if c.post else None,
            "parent_id": c.parent_id
        })
        data.append(d)
    return jsonify({"flagged_comments": data, "count": len(data)}), 200

@admin_bp.route("/admin/users", methods=["GET"])
@admin_required
def get_all_users():
    """Paginated list of users with stats"""
    page     = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    search   = request.args.get('search', '').strip()

    query = User.query
    if search:
        query = query.filter(or_(
            User.username.ilike(f'%{search}%'),
            User.email.ilike(f'%{search}%')
        ))
    pag = query.order_by(User.created_at.desc()).paginate(page, per_page, False)

    users = []
    for u in pag.items:
        d = u.to_dict()
        d.update({
            "posts_count": u.posts.count(),
            "comments_count": u.comments.count(),
            "votes_count": u.votes.count(),
            "flagged_posts": u.posts.filter_by(is_flagged=True).count(),
            "flagged_comments": u.comments.filter_by(is_flagged=True).count()
        })
        users.append(d)

    return jsonify({
        "users": users,
        "pagination": {
            "page": pag.page,
            "per_page": pag.per_page,
            "total": pag.total,
            "pages": pag.pages,
            "has_prev": pag.has_prev,
            "has_next": pag.has_next
        }
    }), 200

@admin_bp.route("/admin/dashboard-summary", methods=["GET"])
@admin_required
def get_dashboard_summary():
    """High-level dashboard overview"""
    try:
        totals = {
            "total_users":    User.query.count(),
            "total_posts":    Post.query.count(),
            "total_comments": Comment.query.count(),
            "blocked_users":  User.query.filter_by(is_blocked=True).count()
        }
        pending = {
            "posts":   Post.query.filter_by(is_approved=False).count(),
            "comments":Comment.query.filter_by(is_approved=False).count()
        }
        flagged = {
            "posts":   Post.query.filter_by(is_flagged=True).count(),
            "comments":Comment.query.filter_by(is_flagged=True).count()
        }
        day_ago = datetime.now(timezone.utc) - timedelta(days=1)
        recent = {
            "users":    User.query.filter(User.created_at>=day_ago).count(),
            "posts":    Post.query.filter(Post.created_at>=day_ago).count(),
            "comments": Comment.query.filter(Comment.created_at>=day_ago).count()
        }

        # Top contributors
        top_posts = db.session.query(
            User.id, User.username, func.count(Post.id).label('count')
        ).join(Post).group_by(User.id).order_by(func.count(Post.id).desc()).limit(5).all()

        top_comments = db.session.query(
            User.id, User.username, func.count(Comment.id).label('count')
        ).join(Comment).group_by(User.id).order_by(func.count(Comment.id).desc()).limit(5).all()

        summary = {
            "overview": totals,
            "pending_approval": {**pending, "total": sum(pending.values())},
            "flagged_content": {**flagged, "total": sum(flagged.values())},
            "recent_activity": recent,
            "top_users": {
                "posters":    [{"id": u.id, "username": u.username, "count": u.count} for u in top_posts],
                "commenters":[{"id": u.id, "username": u.username, "count": u.count} for u in top_comments]
            }
        }
        return jsonify(summary), 200

    except Exception as e:
        current_app.logger.error(f"Error in get_dashboard_summary: {e}")
        return jsonify({"error": "Failed to fetch dashboard summary"}), 500

@admin_bp.route("/admin/users/<int:user_id>/block", methods=["PATCH"])
@admin_required
def toggle_block_user(user_id):
    """Block/unblock a user"""
    user = User.query.get_or_404(user_id)
    me = int(get_jwt_identity())
    if user.id == me:
        return jsonify({"error": "Cannot block yourself"}), 400

    user.is_blocked = not user.is_blocked
    user.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"User {'blocked' if user.is_blocked else 'unblocked'}",
        "user": user.to_dict()
    }), 200

@admin_bp.route("/admin/users/<int:user_id>", methods=["DELETE"])
@admin_required
def delete_user(user_id):
    """Delete a user"""
    user = User.query.get_or_404(user_id)
    me = int(get_jwt_identity())
    if user.id == me:
        return jsonify({"error": "Cannot delete yourself"}), 400

    db.session.delete(user)
    db.session.commit()
    return jsonify({
        "success": True,
        "message": f"User '{user.username}' deleted"
    }), 200

@admin_bp.route("/admin/users/<int:user_id>/admin", methods=["PATCH"])
@admin_required
def toggle_admin_status(user_id):
    """Promote/demote a user"""
    user = User.query.get_or_404(user_id)
    me = int(get_jwt_identity())
    if user.id == me:
        return jsonify({"error": "Cannot modify your own admin status"}), 400

    user.is_admin = not user.is_admin
    user.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"User {'promoted' if user.is_admin else 'demoted'}",
        "user": user.to_dict()
    }), 200

@admin_bp.route("/admin/bulk-actions/approve-posts", methods=["POST"])
@admin_required
def bulk_approve_posts():
    """Bulk approve/disapprove posts"""
    data = request.get_json() or {}
    ids     = data.get('post_ids', [])
    approve = bool(data.get('approve', True))
    if not ids:
        return jsonify({"error": "No post IDs provided"}), 400

    updated = Post.query.filter(Post.id.in_(ids)).update({
        Post.is_approved: approve,
        Post.updated_at:   datetime.now(timezone.utc)
    }, synchronize_session=False)
    db.session.commit()
    return jsonify({
        "success": True,
        "message": f"{updated} posts {'approved' if approve else 'rejected'}"
    }), 200

@admin_bp.route("/admin/bulk-actions/approve-comments", methods=["POST"])
@admin_required
def bulk_approve_comments():
    """Bulk approve/disapprove comments"""
    data = request.get_json() or {}
    ids     = data.get('comment_ids', [])
    approve = bool(data.get('approve', True))
    if not ids:
        return jsonify({"error": "No comment IDs provided"}), 400

    updated = Comment.query.filter(Comment.id.in_(ids)).update({
        Comment.is_approved: approve,
        Comment.updated_at:   datetime.now(timezone.utc)
    }, synchronize_session=False)
    db.session.commit()
    return jsonify({
        "success": True,
        "message": f"{updated} comments {'approved' if approve else 'rejected'}"
    }), 200

@admin_bp.route("/admin/health", methods=["GET"])
@admin_required
def admin_health_check():
    """Admin API health check"""
    return jsonify({
        "status":    "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }), 200