from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    is_blocked = db.Column(db.Boolean, default=False, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    posts = db.relationship(
        "Post", backref="user", lazy=True, cascade="all, delete-orphan"
    )
    comments = db.relationship(
        "Comment", backref="user", lazy=True, cascade="all, delete-orphan"
    )
    votes = db.relationship(
        "Vote", backref="user", lazy="dynamic", cascade="all, delete-orphan"
    )
    likes = db.relationship(
        "Like", backref="user", lazy="dynamic", cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "is_admin": self.is_admin,
            "is_blocked": self.is_blocked,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f"<User {self.username} (admin={self.is_admin})>"


class Post(db.Model):
    __tablename__ = 'posts'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    tags = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    # Approval and flagging
    is_flagged = db.Column(db.Boolean, default=False, nullable=False, index=True)
    is_approved = db.Column(db.Boolean, default=True, nullable=False, index=True)

    # Foreign key
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                        nullable=False, index=True)

    # Relationships
    comments = db.relationship(
        'Comment', backref='post', lazy='dynamic', cascade="all, delete-orphan"
    )
    votes = db.relationship(
        'Vote', backref='post', lazy='dynamic', cascade="all, delete-orphan"
    )
    likes = db.relationship(
        'Like', backref='post', lazy='dynamic', cascade="all, delete-orphan"
    )

    # Computed properties
    @property
    def likes_count(self):
        return self.likes.count()

    @property
    def vote_score(self):
        return sum(v.value for v in self.votes)

    @property
    def upvotes_count(self):
        return self.votes.filter_by(value=1).count()

    @property
    def downvotes_count(self):
        return self.votes.filter_by(value=-1).count()

    @property
    def total_votes(self):
        return self.votes.count()

    @property
    def comments_count(self):
        return self.comments.filter_by(is_approved=True).count()

    def to_dict(self, include_author=True, current_user=None):
        data = {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'tags': self.tags,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_approved': self.is_approved,
            'is_flagged': self.is_flagged,
            'likes_count': self.likes_count,
            'vote_score': self.vote_score,
            'upvotes_count': self.upvotes_count,
            'downvotes_count': self.downvotes_count,
            'total_votes': self.total_votes,
            'comments_count': self.comments_count
        }

        if include_author and self.user:
            data['author'] = {
                'id': self.user.id,
                'username': self.user.username
            }

        if current_user:
            uv = self.votes.filter_by(user_id=current_user.id).first()
            data['user_vote'] = uv.value if uv else None
            ul = self.likes.filter_by(user_id=current_user.id).first()
            data['user_liked'] = bool(ul)

        return data

    def __repr__(self):
        return f"<Post {self.title}>"


class Comment(db.Model):
    __tablename__ = 'comments'

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                        nullable=False, index=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'),
                        nullable=False, index=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('comments.id'),
                          nullable=True, index=True)

    # Approval and flagging
    is_flagged = db.Column(db.Boolean, default=False, nullable=False, index=True)
    is_approved = db.Column(db.Boolean, default=True, nullable=False, index=True)

    # Relationships
    votes = db.relationship(
        'Vote', backref='comment', lazy='dynamic', cascade='all, delete-orphan'
    )
    likes = db.relationship(
        'Like', backref='comment', lazy='dynamic', cascade='all, delete-orphan'
    )
    replies = db.relationship(
        'Comment',
        backref=db.backref('parent', remote_side=[id]),
        lazy='dynamic'
    )

    # Computed properties
    @property
    def likes_count(self):
        return self.likes.count()

    @property
    def vote_score(self):
        return sum(v.value for v in self.votes)

    @property
    def upvotes_count(self):
        return self.votes.filter_by(value=1).count()

    @property
    def downvotes_count(self):
        return self.votes.filter_by(value=-1).count()

    @property
    def total_votes(self):
        return self.votes.count()

    @property
    def replies_count(self):
        return self.replies.filter_by(is_approved=True).count()

    def to_dict(self, include_author=True, current_user=None):
        data = {
            'id': self.id,
            'content': self.content,
            'post_id': self.post_id,
            'parent_id': self.parent_id,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_approved': self.is_approved,
            'is_flagged': self.is_flagged,
            'likes_count': self.likes_count,
            'vote_score': self.vote_score,
            'upvotes_count': self.upvotes_count,
            'downvotes_count': self.downvotes_count,
            'total_votes': self.total_votes,
            'replies_count': self.replies_count
        }

        if include_author and self.user:
            data['author'] = {
                'id': self.user.id,
                'username': self.user.username
            }

        if current_user:
            uv = self.votes.filter_by(user_id=current_user.id).first()
            data['user_vote'] = uv.value if uv else None
            ul = self.likes.filter_by(user_id=current_user.id).first()
            data['user_liked'] = bool(ul)

        return data

    def __repr__(self):
        return f"<Comment {self.content[:20]}...>"


class Vote(db.Model):
    __tablename__ = 'votes'

    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.Integer, nullable=False)  # 1 or -1
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           nullable=False)

    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                        nullable=False, index=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'),
                        nullable=True, index=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('comments.id'),
                           nullable=True, index=True)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'post_id', name='unique_user_post_vote'),
        db.UniqueConstraint('user_id', 'comment_id', name='unique_user_comment_vote'),
        db.CheckConstraint('value IN (1, -1)', name='valid_vote_value'),
        db.CheckConstraint(
            '(post_id IS NOT NULL AND comment_id IS NULL) OR '
            '(post_id IS NULL AND comment_id IS NOT NULL)',
            name='vote_target_constraint'
        ),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'post_id': self.post_id,
            'comment_id': self.comment_id,
            'value': self.value,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        target = f"Post {self.post_id}" if self.post_id else f"Comment {self.comment_id}"
        return f"<Vote user_id={self.user_id} {target} value={self.value}>"


class Like(db.Model):
    __tablename__ = 'likes'

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           nullable=False)

    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                        nullable=False, index=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'),
                        nullable=True, index=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('comments.id'),
                           nullable=True, index=True)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'post_id', name='unique_user_post_like'),
        db.UniqueConstraint('user_id', 'comment_id', name='unique_user_comment_like'),
        db.CheckConstraint(
            '(post_id IS NOT NULL AND comment_id IS NULL) OR '
            '(post_id IS NULL AND comment_id IS NOT NULL)',
            name='like_target_constraint'
        ),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'post_id': self.post_id,
            'comment_id': self.comment_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        target = f"Post {self.post_id}" if self.post_id else f"Comment {self.comment_id}"
        return f"<Like user_id={self.user_id} {target}>"


class TokenBlocklist(db.Model):
    __tablename__ = 'token_blocklist'

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, unique=True, index=True)
    created_at = db.Column(db.DateTime, nullable=False,
                           default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<TokenBlocklist {self.jti}>"