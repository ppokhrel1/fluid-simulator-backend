from fastcrud import FastCRUD

from src.app.models.post import Post
from src.app.schemas.post import PostCreateInternal, PostDelete, PostRead, PostUpdate, PostUpdateInternal

CRUDPost = FastCRUD[Post, PostCreateInternal, PostUpdate, PostUpdateInternal, PostDelete, PostRead]
crud_posts = CRUDPost(Post)
