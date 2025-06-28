from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from functools import wraps
from datetime import datetime, timezone, timedelta
from sqlalchemy import func, and_, or_
from models import db, User, Post, Comment, Vote, Like
import logging

logger = logging.getLogger(__name__)

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
        total_likes = Like.query.count()
        
        # User status counts
        blocked_users = User.query.filter_by(is_blocked=True).count()
        admin_users = User.query.filter_by(is_admin=True).count()
        active_users = User.query.filter_by(is_active=True).count()
        
        # Approval status counts (with safe attribute checking)
        flagged_posts = 0
        flagged_comments = 0
        pending_posts = 0
        pending_comments = 0
        approved_posts = 0
        approved_comments = 0
        
        try:
            if hasattr(Post, 'is_flagged'):
                flagged_posts = Post.query.filter_by(is_flagged=True).count()
            if hasattr(Comment, 'is_flagged'):
                flagged_comments = Comment.query.filter_by(is_flagged=True).count()
            if hasattr(Post, 'is_approved'):
                pending_posts = Post.query.filter_by(is_approved=False).count()
                approved_posts = Post.query.filter_by(is_approved=True).count()
            else:
                approved_posts = total_posts
            if hasattr(Comment, 'is_approved'):
                pending_comments = Comment.query.filter_by(is_approved=False).count()
                approved_comments = Comment.query.filter_by(is_approved=True).count()
            else:
                approved_comments = total_comments
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
            # Basic totals
            "users": total_users,
            "posts": total_posts,
            "comments": total_comments,
            "votes": total_votes,
            "likes": total_likes,
            
            # Content status
            "approved_posts": approved_posts,
            "unapproved_posts": pending_posts,
            "flagged_posts": flagged_posts,
            "approved_comments": approved_comments,
            "unapproved_comments": pending_comments,
            "flagged_comments": flagged_comments,
            
            # Legacy fields for compatibility
            "flagged": flagged_posts + flagged_comments,
            "pending_posts": pending_posts,
            "pending_comments": pending_comments,
            
            # User status
            "active_users": active_users,
            "blocked_users": blocked_users,
            "admin_users": admin_users,
            
            # Recent activity
            "recent_activity": {
                "users": recent_users,
                "posts": recent_posts,
                "comments": recent_comments
            },
            "today_activity": {
                "users": today_users,
                "posts": today_posts,
                "comments": today_comments
            },
            
            # Ratios for dashboard
            "approval_rate": round((approved_posts / total_posts * 100) if total_posts > 0 else 0, 1),
            "comment_approval_rate": round((approved_comments / total_comments * 100) if total_comments > 0 else 0, 1)
        }
        
        current_app.logger.info(f"Admin stats retrieved successfully")
        return jsonify(stats), 200
        
    except Exception as e:
        current_app.logger.error(f"Error fetching admin stats: {e}")
        return jsonify({"error": "Failed to fetch admin stats", "message": str(e)}), 500

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
        
        current_app.logger.info(f"Activity trends retrieved successfully")
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
            
        posts = Post.query.join(User, Post.user_id == User.id)\
                         .filter(Post.is_flagged == True)\
                         .order_by(Post.created_at.desc())\
                         .all()
        
        posts_data = []
        for post in posts:
            try:
                post_dict = post.to_dict(include_author=True)
                # Add extra information
                post_dict.update({
                    "flagged_at": post.updated_at.isoformat() if hasattr(post, 'updated_at') and post.updated_at else post.created_at.isoformat(),
                    "comments_count": post.comments.count(),
                    "likes_count": post.likes_count,
                    "vote_score": post.vote_score,
                    "approved_comments": post.comments.filter_by(is_approved=True).count() if hasattr(Comment, 'is_approved') else post.comments.count()
                })
            except Exception as e:
                # Fallback to basic serialization
                post_dict = {
                    "id": post.id,
                    "title": post.title,
                    "content": post.content,
                    "user_id": post.user_id,
                    "author": {
                        "id": post.user.id,
                        "username": post.user.username
                    } if post.user else {"id": None, "username": "Unknown"},
                    "created_at": post.created_at.isoformat(),
                    "is_flagged": getattr(post, 'is_flagged', False),
                    "is_approved": getattr(post, 'is_approved', True)
                }
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
            
        comments = Comment.query.join(User, Comment.user_id == User.id)\
                              .filter(Comment.is_flagged == True)\
                              .order_by(Comment.created_at.desc())\
                              .all()
        
        comments_data = []
        for comment in comments:
            try:
                comment_dict = comment.to_dict(include_author=True)
                # Add extra information
                comment_dict.update({
                    "flagged_at": comment.updated_at.isoformat() if hasattr(comment, 'updated_at') and comment.updated_at else comment.created_at.isoformat(),
                    "post_title": comment.post.title if comment.post else "Unknown Post",
                    "parent_comment_id": comment.parent_id,
                    "likes_count": comment.likes_count,
                    "vote_score": comment.vote_score
                })
            except Exception as e:
                # Fallback to basic serialization
                comment_dict = {
                    "id": comment.id,
                    "content": comment.content,
                    "user_id": comment.user_id,
                    "post_id": comment.post_id,
                    "author": {
                        "id": comment.user.id,
                        "username": comment.user.username
                    } if comment.user else {"id": None, "username": "Unknown"},
                    "created_at": comment.created_at.isoformat(),
                    "is_flagged": getattr(comment, 'is_flagged', False),
                    "is_approved": getattr(comment, 'is_approved', True)
                }
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

@admin_bp.route("/admin/posts", methods=["GET"])
@admin_required
def get_all_posts():
    """Get all posts with enhanced information for admin"""
    try:
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        
        # Get search parameter
        search = request.args.get('search', '').strip()
        status = request.args.get('status', 'all')  # 'all', 'approved', 'unapproved', 'flagged'
        
        # Build query with join for author information
        query = Post.query.join(User, Post.user_id == User.id)
        
        if search:
            query = query.filter(
                or_(
                    Post.title.ilike(f'%{search}%'),
                    Post.content.ilike(f'%{search}%'),
                    User.username.ilike(f'%{search}%')
                )
            )
        
        # Filter by status
        if status == 'approved' and hasattr(Post, 'is_approved'):
            query = query.filter(Post.is_approved == True)
        elif status == 'unapproved' and hasattr(Post, 'is_approved'):
            query = query.filter(Post.is_approved == False)
        elif status == 'flagged' and hasattr(Post, 'is_flagged'):
            query = query.filter(Post.is_flagged == True)
        
        # Order by creation date (newest first)
        query = query.order_by(Post.created_at.desc())
        
        # Paginate if requested, otherwise get all
        if request.args.get('paginate', 'false').lower() == 'true':
            posts_pagination = query.paginate(
                page=page, per_page=per_page, error_out=False
            )
            posts = posts_pagination.items
        else:
            posts = query.all()
        
        posts_data = []
        for post in posts:
            try:
                # Use the model's to_dict method with current user context
                current_user_id = get_jwt_identity()
                current_user = User.query.get(current_user_id)
                post_dict = post.to_dict(include_author=True, current_user=current_user)
                
            except Exception as e:
                current_app.logger.warning(f"Error serializing post {post.id}: {e}")
                # Fallback to basic dict
                post_dict = {
                    "id": post.id,
                    "title": post.title,
                    "content": post.content,
                    "created_at": post.created_at.isoformat(),
                    "user_id": post.user_id,
                    "author": {
                        "id": post.user.id,
                        "username": post.user.username,
                        "avatar_url": getattr(post.user, 'avatar_url', None)
                    } if post.user else {"id": None, "username": "Unknown"},
                    "is_approved": getattr(post, 'is_approved', True),
                    "is_flagged": getattr(post, 'is_flagged', False),
                    "comments_count": post.comments.count(),
                    "likes_count": post.likes.count() if hasattr(post, 'likes') else 0,
                    "vote_score": sum(vote.value for vote in post.votes) if hasattr(post, 'votes') else 0
                }
                
            posts_data.append(post_dict)
        
        # Return with or without pagination info
        if request.args.get('paginate', 'false').lower() == 'true':
            return jsonify({
                "posts": posts_data,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": posts_pagination.total,
                    "pages": posts_pagination.pages,
                    "has_prev": posts_pagination.has_prev,
                    "has_next": posts_pagination.has_next
                }
            }), 200
        else:
            return jsonify(posts_data), 200
        
    except Exception as e:
        current_app.logger.error(f"Error fetching admin posts: {e}")
        return jsonify({"error": "Failed to fetch posts"}), 500

@admin_bp.route("/admin/comments", methods=["GET"])
@admin_required
def get_all_comments():
    """Get all comments with enhanced information for admin"""
    try:
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 200)
        
        # Get search parameter
        search = request.args.get('search', '').strip()
        
        # Get post filter
        post_id = request.args.get('post_id', type=int)
        user_id = request.args.get('user_id', type=int)
        
        # Build query with join for author information
        query = Comment.query.join(User, Comment.user_id == User.id)
        
        if search:
            query = query.filter(Comment.content.ilike(f'%{search}%'))
        
        if post_id:
            query = query.filter_by(post_id=post_id)
            
        if user_id:
            query = query.filter_by(user_id=user_id)
        
        # Order by creation date (newest first)
        query = query.order_by(Comment.created_at.desc())
        
        # Paginate if requested, otherwise get all
        if request.args.get('paginate', 'false').lower() == 'true':
            comments_pagination = query.paginate(
                page=page, per_page=per_page, error_out=False
            )
            comments = comments_pagination.items
        else:
            comments = query.all()
        
        comments_data = []
        for comment in comments:
            try:
                # Use the model's to_dict method with current user context
                current_user_id = get_jwt_identity()
                current_user = User.query.get(current_user_id)
                comment_dict = comment.to_dict(include_author=True, current_user=current_user)
                
                # Add extra information
                comment_dict.update({
                    "post_title": comment.post.title if comment.post else "Unknown Post"
                })
                
            except Exception as e:
                current_app.logger.warning(f"Error serializing comment {comment.id}: {e}")
                # Fallback to basic dict
                comment_dict = {
                    "id": comment.id,
                    "content": comment.content,
                    "created_at": comment.created_at.isoformat(),
                    "post_id": comment.post_id,
                    "user_id": comment.user_id,
                    "author": {
                        "id": comment.user.id,
                        "username": comment.user.username,
                        "avatar_url": getattr(comment.user, 'avatar_url', None)
                    } if comment.user else {"id": None, "username": "Unknown"},
                    "is_approved": getattr(comment, 'is_approved', True),
                    "is_flagged": getattr(comment, 'is_flagged', False),
                    "post_title": comment.post.title if comment.post else "Unknown Post",
                    "likes_count": comment.likes.count() if hasattr(comment, 'likes') else 0,
                    "vote_score": sum(vote.value for vote in comment.votes) if hasattr(comment, 'votes') else 0
                }
                
            comments_data.append(comment_dict)
        
        # Return with or without pagination info
        if request.args.get('paginate', 'false').lower() == 'true':
            return jsonify({
                "comments": comments_data,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": comments_pagination.total,
                    "pages": comments_pagination.pages,
                    "has_prev": comments_pagination.has_prev,
                    "has_next": comments_pagination.has_next
                }
            }), 200
        else:
            return jsonify(comments_data), 200
        
    except Exception as e:
        current_app.logger.error(f"Error fetching admin comments: {e}")
        return jsonify({"error": "Failed to fetch comments"}), 500

@admin_bp.route("/admin/all-comments", methods=["GET"])
@admin_required  
def get_all_comments_simple():
    """Simple endpoint to get all comments (alternative route)"""
    try:
        comments = Comment.query.join(User, Comment.user_id == User.id)\
                              .order_by(Comment.created_at.desc())\
                              .all()
        comments_data = []
        
        for comment in comments:
            try:
                current_user_id = get_jwt_identity()
                current_user = User.query.get(current_user_id)
                comment_dict = comment.to_dict(include_author=True, current_user=current_user)
            except Exception as e:
                # Fallback to basic dict if to_dict fails
                comment_dict = {
                    "id": comment.id,
                    "content": comment.content,
                    "created_at": comment.created_at.isoformat(),
                    "post_id": comment.post_id,
                    "user_id": comment.user_id,
                    "author": {
                        "id": comment.user.id,
                        "username": comment.user.username
                    } if comment.user else {"id": None, "username": "Unknown"}
                }
            comments_data.append(comment_dict)
        
        return jsonify(comments_data), 200
        
    except Exception as e:
        current_app.logger.error(f"Error fetching all comments: {e}")
        return jsonify({"error": "Failed to fetch comments"}), 500

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

# Content management endpoints with proper error handling
@admin_bp.route("/admin/posts/<int:post_id>/approve", methods=["PATCH"])
@admin_required
def approve_post(post_id):
    """Approve or disapprove a post"""
    try:
        post = Post.query.get_or_404(post_id)
        
        # Check if model has is_approved attribute
        if not hasattr(Post, 'is_approved'):
            current_app.logger.warning("Post model missing is_approved attribute")
            return jsonify({"error": "Post approval not supported - model missing is_approved field"}), 400
        
        data = request.get_json() or {}
        if "is_approved" in data:
            post.is_approved = bool(data["is_approved"])
        else:
            current_value = getattr(post, 'is_approved', True)
            post.is_approved = not current_value

        if hasattr(post, 'updated_at'):
            post.updated_at = datetime.now(timezone.utc)
        db.session.commit()

        action = "approved" if post.is_approved else "disapproved"
        current_app.logger.info(f"Post {post.id} {action} by admin")

        return jsonify({
            "success": True,
            "message": f"Post {action} successfully",
            "is_approved": post.is_approved
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error approving post: {e}")
        return jsonify({"error": f"Failed to update post approval status: {str(e)}"}), 500

@admin_bp.route('/admin/posts/<int:post_id>/flag', methods=['PATCH'])
@admin_required
def flag_post(post_id):
    """Flag or unflag a post"""
    try:
        post = Post.query.get_or_404(post_id)
        
        # Check if model has is_flagged attribute
        if not hasattr(Post, 'is_flagged'):
            current_app.logger.warning("Post model missing is_flagged attribute")
            return jsonify({"error": "Post flagging not supported - model missing is_flagged field"}), 400
        
        data = request.get_json() or {}
        if "is_flagged" in data:
            post.is_flagged = bool(data["is_flagged"])
        else:
            current_value = getattr(post, 'is_flagged', False)
            post.is_flagged = not current_value

        if hasattr(post, 'updated_at'):
            post.updated_at = datetime.now(timezone.utc)
        db.session.commit()

        action = "flagged" if post.is_flagged else "unflagged"
        current_app.logger.info(f"Post {post.id} {action} by admin")

        return jsonify({
            "success": True,
            "message": f"Post {action} successfully",
            "is_flagged": post.is_flagged
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error flagging post: {e}")
        return jsonify({"error": f"Failed to update post flag status: {str(e)}"}), 500

@admin_bp.route("/admin/comments/<int:comment_id>/approve", methods=["PATCH"])
@admin_required
def approve_comment_admin(comment_id):
    """Approve or disapprove a comment (admin endpoint)"""
    try:
        comment = Comment.query.get_or_404(comment_id)
        
        # Check if model has is_approved attribute
        if not hasattr(Comment, 'is_approved'):
            current_app.logger.warning("Comment model missing is_approved attribute")
            return jsonify({"error": "Comment approval not supported - model missing is_approved field"}), 400
        
        data = request.get_json() or {}
        if "is_approved" in data:
            comment.is_approved = bool(data["is_approved"])
        else:
            current_value = getattr(comment, 'is_approved', True)
            comment.is_approved = not current_value

        if hasattr(comment, 'updated_at'):
            comment.updated_at = datetime.now(timezone.utc)
        db.session.commit()

        action = "approved" if comment.is_approved else "disapproved"
        current_app.logger.info(f"Comment {comment.id} {action} by admin")

        return jsonify({
            "success": True,
            "message": f"Comment {action} successfully",
            "is_approved": comment.is_approved
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error approving comment: {e}")
        return jsonify({"error": f"Failed to update comment approval status: {str(e)}"}), 500

@admin_bp.route('/admin/comments/<int:comment_id>/flag', methods=['PATCH'])
@admin_required
def flag_comment_admin(comment_id):
    """Flag or unflag a comment (admin endpoint)"""
    try:
        comment = Comment.query.get_or_404(comment_id)
        
        # Check if model has is_flagged attribute
        if not hasattr(Comment, 'is_flagged'):
            current_app.logger.warning("Comment model missing is_flagged attribute")
            return jsonify({"error": "Comment flagging not supported - model missing is_flagged field"}), 400
        
        data = request.get_json() or {}
        if "is_flagged" in data:
            comment.is_flagged = bool(data["is_flagged"])
        else:
            current_value = getattr(comment, 'is_flagged', False)
            comment.is_flagged = not current_value

        if hasattr(comment, 'updated_at'):
            comment.updated_at = datetime.now(timezone.utc)
        db.session.commit()

        action = "flagged" if comment.is_flagged else "unflagged"
        current_app.logger.info(f"Comment {comment.id} {action} by admin")

        return jsonify({
            "success": True,
            "message": f"Comment {action} successfully",
            "is_flagged": comment.is_flagged
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error flagging comment: {e}")
        return jsonify({"error": f"Failed to update comment flag status: {str(e)}"}), 500

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

# Test endpoint to verify admin endpoints work
@admin_bp.route("/admin/test", methods=["GET"])
@admin_required
def test_admin_endpoints():
    """Test endpoint to verify admin functionality"""
    try:
        # Test model attributes
        has_post_flags = hasattr(Post, 'is_flagged') and hasattr(Post, 'is_approved')
        has_comment_flags = hasattr(Comment, 'is_flagged') and hasattr(Comment, 'is_approved')
        
        return jsonify({
            "success": True,
            "message": "Admin endpoints working",
            "model_attributes": {
                "post_has_approval_flags": has_post_flags,
                "comment_has_approval_flags": has_comment_flags,
                "post_approval": hasattr(Post, 'is_approved'),
                "post_flagging": hasattr(Post, 'is_flagged'),
                "comment_approval": hasattr(Comment, 'is_approved'),
                "comment_flagging": hasattr(Comment, 'is_flagged')
            },
            "available_endpoints": [
                "GET /api/admin/stats",
                "GET /api/admin/posts", 
                "GET /api/admin/comments",
                "PATCH /api/admin/posts/<id>/flag",
                "PATCH /api/admin/comments/<id>/flag",
                "PATCH /api/admin/posts/<id>/approve",
                "PATCH /api/admin/comments/<id>/approve"
            ],
            "user_id": get_jwt_identity()
        }), 200
    except Exception as e:
        return jsonify({"error": f"Test failed: {str(e)}"}), 500