from pydantic import BaseModel


class FolderCreate(BaseModel):
    name: str
    parent_id: int | None = None


class FolderRename(BaseModel):
    name: str


class Folder(BaseModel):
    id: int
    name: str
    parent_id: int | None = None
    created_at: str
    children: list["Folder"] = []


class ArchiveVersion(BaseModel):
    id: int
    version_number: int
    filename: str
    size_bytes: int
    checksum: str
    created_at: str


class Archive(BaseModel):
    id: int
    folder_id: int
    name: str
    status: str
    created_at: str
    version_count: int = 0
    latest_version: ArchiveVersion | None = None


class Comment(BaseModel):
    id: int
    action: str
    text: str
    version_number: int | None = None
    created_at: str
    user_name: str | None = None


class CommentCreate(BaseModel):
    text: str


class StatusChange(BaseModel):
    status: str
    comment: str | None = None


# ---------- Auth / Benutzer ----------

class LoginRequest(BaseModel):
    username: str
    password: str


class UserInfo(BaseModel):
    id: int
    username: str
    display_name: str | None = None
    role: str


class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "user"
    display_name: str | None = None


class UserUpdate(BaseModel):
    password: str | None = None
    role: str | None = None
    display_name: str | None = None


class UserWithPermissions(UserInfo):
    permissions: list[int] = []


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class PermissionGrant(BaseModel):
    user_id: int
    folder_id: int