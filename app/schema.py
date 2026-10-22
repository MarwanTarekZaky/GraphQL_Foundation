from enum import Enum
from typing import Annotated
import asyncio
from collections.abc import AsyncGenerator

import strawberry

from app.graphql_errors import ErrorCodes
from app.errors import ErrorCode, ValidationError

from app.database import (
    get_user_full_name,
    get_user_nickname,
    get_all_reviews,
    get_reviews_by_author,
    get_user_avatar_url,
)

from app.events import subscribe_to_review_created

from app.services import (
    write_review,
    remove_review,
    change_nickname,
    set_avatar,
    request_avatar_upload,
    get_email,
    get_review_count,
    list_reviews,
    
)


# ============================================================
# USER
# ============================================================

@strawberry.type
class User:
    id: int

    @strawberry.field
    async def full_name(self) -> str | None:
        return await get_user_full_name(self.id)

    @strawberry.field
    async def nickname(self) -> str | None:
        return await get_user_nickname(self.id)
    
    @strawberry.field
    async def avatar_url(self, info: strawberry.Info) -> str | None:
        path = await get_user_avatar_url(self.id)
    
        if path is None:
            return None
    
        base_url = str(info.context["request"].base_url).rstrip("/")
        return base_url + path
    
    @strawberry.field
    async def email(self, info: strawberry.Info) -> str | None:
        return await get_email(
            viewer=info.context["user"],
            user_id=self.id,
        )
        
    @strawberry.field
    async def reviews_connection(
            self,
            first: int = 10,
            after: str | None = None,
        ) -> "ReviewConnection | None":
            page = await list_reviews(first=first, after=after, author_id=self.id)
            return ReviewConnection.from_page(page, author_id=self.id)
    
    @strawberry.field(
    deprecation_reason="Use `reviewsConnection`."
    )
    async def reviews(self) -> list["Review"]:
        documents = await get_reviews_by_author(self.id)
        return [Review.from_document(doc) for doc in documents]

    @strawberry.field(
        deprecation_reason="Use `fullName`."
    )
    async def name(self) -> str | None:
        return await get_user_full_name(self.id)
    
    
    



# ============================================================
# ENUM USED BY STARSHIP
# ============================================================

@strawberry.enum
class LengthUnit(Enum):
    METER = "METER"
    FOOT = "FOOT"


@strawberry.enum
class Episode(Enum):
    NEWHOPE = "NEWHOPE"
    EMPIRE = "EMPIRE"
    JEDI = "JEDI"
    
# ============================================================
# CHARACTER INTERFACE
# ============================================================

@strawberry.interface
class Character:
    id: strawberry.ID
    name: str


# ============================================================
# HUMAN IMPLEMENTS CHARACTER
# ============================================================

@strawberry.type
class Human(Character):
    height: float
    total_credits: int


# ============================================================
# DROID IMPLEMENTS CHARACTER
# ============================================================

@strawberry.type
class Droid(Character):
    primary_function: str


# ============================================================
# STARSHIP
# ============================================================

@strawberry.type
class Starship:
    id: strawberry.ID
    name: str

    # Used internally by Python but not exposed in GraphQL.
    length_in_meters: strawberry.Private[float]

    @strawberry.field
    def length(
        self,
        unit: LengthUnit = LengthUnit.METER,
    ) -> float:
        if unit == LengthUnit.FOOT:
            return self.length_in_meters * 3.28084

        return self.length_in_meters


# ============================================================
# UNION
# ============================================================

SearchResult = Annotated[
    Human | Droid | Starship,
    strawberry.union("SearchResult"),
]


# ============================================================
# TEMPORARY DATA
# ============================================================

DROIDS = {
    "2000": Droid(
        id="2000",
        name="C-3PO",
        primary_function="Protocol",
    ),
    "2001": Droid(
        id="2001",
        name="R2-D2",
        primary_function="Astromech",
    ),
}


SEARCH_DATA: list[Human | Droid | Starship] = [
    Human(
        id="1001",
        name="Han Solo",
        height=1.8,
        total_credits=10000,
    ),
    Human(
        id="1002",
        name="Leia Organa",
        height=1.5,
        total_credits=20000,
    ),
    Droid(
        id="2001",
        name="R2-D2",
        primary_function="Astromech",
    ),
    Starship(
        id="3001",
        name="TIE Advanced x1",
        length_in_meters=9.2,
    ),
]


# ============================================================
# INPUT AND OUTPUT TYPES FOR REVIEW
# ============================================================

@strawberry.input
class ReviewInput:
    stars: int
    commentary: str | None = None


@strawberry.type
class Review:
    id: strawberry.ID
    episode: Episode
    stars: int
    commentary: str | None
    author_id: int = strawberry.field(
        deprecation_reason="Use `author { id }`."
    )
    
    @strawberry.field
    def author(self) -> User:
        return User(id=self.author_id)
    
    
    @classmethod
    def from_document(cls, document: dict) -> "Review":
        return cls(
            id=document["id"],
            episode=Episode(document["episode"]),
            stars=document["stars"],
            commentary=document.get("commentary"),
            author_id=document["authorId"],
        )
       
        
# ============================================================
# PAGINATION (Relay cursor connections)
# ============================================================

@strawberry.type
class PageInfo:
    has_next_page: bool
    has_previous_page: bool
    start_cursor: str | None
    end_cursor: str | None


@strawberry.type
class ReviewEdge:
    cursor: str
    node: Review


@strawberry.type
class ReviewConnection:
    edges: list[ReviewEdge]
    page_info: PageInfo

    # Which list this page belongs to (None = all reviews). Not exposed.
    author_id: strawberry.Private[int | None]

    @strawberry.field
    def nodes(self) -> list[Review]:
        # Shortcut for clients that don't need edge data like cursors.
        return [edge.node for edge in self.edges]

    @strawberry.field
    async def total_count(self) -> int:
        # Only counted when a client actually asks for it.
        return await get_review_count(author_id=self.author_id)

    @classmethod
    def from_page(cls, page: dict, author_id: int | None) -> "ReviewConnection":
        edges = [
            ReviewEdge(
                cursor=edge["cursor"],
                node=Review.from_document(edge["node"]),
            )
            for edge in page["edges"]
        ]

        return cls(
            edges=edges,
            page_info=PageInfo(
                has_next_page=page["has_next_page"],
                has_previous_page=page["has_previous_page"],
                start_cursor=edges[0].cursor if edges else None,
                end_cursor=edges[-1].cursor if edges else None,
            ),
            author_id=author_id,
        )


@strawberry.type
class Friend:
    id: strawberry.ID
    name: str
    
@strawberry.type
class HeroWithFriends:
    id: strawberry.ID
    name: str
    friends: list[Friend]

# ============================================================
# ERRORS AS DATA
# ============================================================

strawberry.enum(ErrorCode, name="UserErrorCode")


@strawberry.type
class UserError:
    message: str
    code: ErrorCode
    # Path to the input field that caused the error, e.g. ["stars"].
    field: list[str] | None = None

    @classmethod
    def from_exception(cls, error: ValidationError) -> "UserError":
        return cls(
            message=error.message,
            code=error.code,
            field=error.field,
        )


@strawberry.input
class AddReviewInput:
    episode: Episode
    stars: int
    commentary: str | None = None


@strawberry.type
class AddReviewPayload:
    review: Review | None = None
    user_errors: list[UserError] = strawberry.field(default_factory=list)
  
@strawberry.type
class DeleteReviewPayload:
    success: bool
    delete_review_id: strawberry.ID | None
    message: str = strawberry.field(
        deprecation_reason="Use `userErrors`."
    )
    user_errors: list["UserError"] = strawberry.field(default_factory=list)
    
@strawberry.type
class AvatarUpload:
    upload_id: strawberry.ID
    upload_url: str
    expires_at: int

  
# ============================================================
# QUERY ROOT
# ============================================================

@strawberry.type
class Query:

    # --------------------------------------------------------
    # Authenticated MongoDB user example
    # --------------------------------------------------------

    @strawberry.field
    async def me(
        self,
        info: strawberry.Info,
    ) -> User | None:
        authenticated_user = info.context["user"]

        if authenticated_user is None:
            return None

        return User(
            id=authenticated_user["id"],
        )

    # --------------------------------------------------------
    # Interface examples
    # --------------------------------------------------------

    @strawberry.field
    async def hero(self) -> Character:
        return Droid(
            id="2001",
            name="R2-D2",
            primary_function="Astromech",
        )

    @strawberry.field
    async def human_hero(self) -> Character:
        return Human(
            id="1000",
            name="Luke Skywalker",
            height=1.72,
            total_credits=1000,
        )

    # --------------------------------------------------------
    # Starship and field argument example
    # --------------------------------------------------------

    @strawberry.field
    async def starship(self) -> Starship:
        return Starship(
            id="millennium-falcon",
            name="Millennium Falcon",
            length_in_meters=34.75,
        )

    # --------------------------------------------------------
    # Query root and required ID argument example
    # --------------------------------------------------------

    @strawberry.field
    async def droid(
        self,
        id: strawberry.ID,
    ) -> Droid | None:
        return DROIDS.get(str(id))

    # --------------------------------------------------------
    # Union example
    # --------------------------------------------------------

    @strawberry.field
    async def search(
        self,
        text: str,
    ) -> list[SearchResult]:
        normalized_text = text.lower()
        results = []

        for item in SEARCH_DATA:
            if normalized_text in item.name.lower():
                results.append(item)

        return results
    
    
    @strawberry.field
    async def hero_with_friends(self) -> HeroWithFriends:
        return HeroWithFriends(
            id="2001",
            name="R2-D2",
            friends=[
                Friend(
                    id="1000",
                    name="Luke Skywalker",
                ),
                Friend(
                    id="1001",
                    name="Han Solo",
                ),
                Friend(
                    id="1002",
                    name="Leia Organa",
                ),
            ],  
        )
        
    @strawberry.field
    def boom(self) -> str | None:
        raise RuntimeError("mongodb://admin:SECRET@db failed")

   
    
# ============================================================
# REVIEW QUERIES
# ============================================================

    @strawberry.field
    async def reviews_connection(
        self,
        first: int = 10,
        after: str | None = None,
    ) -> ReviewConnection | None:
        page = await list_reviews(first=first, after=after)
        return ReviewConnection.from_page(page, author_id=None)

    @strawberry.field(
        deprecation_reason="Use `reviewsConnection`."
    )
    async def reviews(self) -> list[Review]:
        review_documents = await get_all_reviews()
        return [Review.from_document(document) for document in review_documents]

# ============================================================
# MUTATION ROOT
# ============================================================

@strawberry.type
class Mutation:
    
    @strawberry.mutation
    async def request_avatar_upload(
        self,
        info: strawberry.Info,
    ) -> AvatarUpload:
        upload = await request_avatar_upload(user=info.context["user"])

        base_url = str(info.context["request"].base_url).rstrip("/")

        return AvatarUpload(
            upload_id=upload["upload_id"],
            upload_url=base_url + upload["path"],
            expires_at=upload["expires"],
        )

    @strawberry.mutation
    async def set_my_avatar(
        self,
        info: strawberry.Info,
        upload_id: strawberry.ID,
    ) -> User:
        updated_user = await set_avatar(
            user=info.context["user"],
            upload_id=str(upload_id),
        )

        return User(id=updated_user["id"])
    

    @strawberry.mutation
    async def add_review(
        self,
        info: strawberry.Info,
        input: AddReviewInput,
    ) -> AddReviewPayload:
        try:
            saved_review = await write_review(
                user=info.context["user"],
                episode=input.episode.value,
                stars=input.stars,
                commentary=input.commentary,
            )
        except ValidationError as error:
            return AddReviewPayload(user_errors=[UserError.from_exception(error)])

        return AddReviewPayload(review=Review.from_document(saved_review))

    @strawberry.mutation(
        deprecation_reason="Use `addReview`, which returns errors as data."
    )
    async def create_review(
        self,
        info: strawberry.Info,
        episode: Episode,
        review: ReviewInput,
    ) -> Review:
        saved_review = await write_review(
            user=info.context["user"],
            episode=episode.value,
            stars=review.stars,
            commentary=review.commentary,
        )

        return Review.from_document(saved_review)

    @strawberry.mutation
    async def update_my_nickname(
        self,
        info: strawberry.Info,
        nickname: str,
    ) -> User:
        updated_user = await change_nickname(
            user=info.context["user"],
            nickname=nickname,
        )

        return User(id=updated_user["id"])

    @strawberry.mutation
    async def delete_review(
        self,
        info: strawberry.Info,
        review_id: strawberry.ID,
    ) -> DeleteReviewPayload:
        deleted_review = await remove_review(
            user=info.context["user"],
            review_id=str(review_id),
        )
        
        if deleted_review is None:
            return DeleteReviewPayload(
                success=False,
                delete_review_id=None,
                message="Review not found or not authorized to delete.",
                user_errors=[
                    UserError(
                        message="Review not found.",
                        code=ErrorCode.REVIEW_NOT_FOUND,
                        field=["reviewId"],
                    )
                ],
            )

        if deleted_review is None:
            return DeleteReviewPayload(
                success=False,
                delete_review_id=None,
                message="Review not found or not authorized to delete.",
            )

        return DeleteReviewPayload(
            success=True,
            delete_review_id=review_id,
            message="Review successfully deleted.",
        )

    @strawberry.mutation(
        deprecation_reason="Use `deleteReview`. Admins can delete any review, not only their own."
    )
    async def delete_my_review(
        self,
        info: strawberry.Info,
        review_id: strawberry.ID,
    ) -> DeleteReviewPayload:
        return await Mutation.delete_review(self, info, review_id)

 
# ============================================================
# Subscriptions
# ============================================================

@strawberry.type
class Subscription:
    
    @strawberry.subscription
    async def count(
        self,
        target: int = 5,
    ) -> AsyncGenerator[int, None]:
        
        for i in range(target):
            yield i
            await asyncio.sleep(1)

    @strawberry.subscription
    async def review_created(
        self,
    ) -> AsyncGenerator[Review, None]:
        async for document in subscribe_to_review_created():
            yield Review.from_document(document)
            
    
# ============================================================
# GRAPHQL SCHEMA
# ============================================================

schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    subscription=Subscription,
    extensions=[ErrorCodes],
)