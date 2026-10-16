from enum import Enum
from typing import Annotated
import asyncio
from collections.abc import AsyncGenerator

import strawberry

from app.database import (
    get_user_full_name,
    get_user_nickname,
    create_review,
    get_all_reviews,
    update_user_nickname,
    delete_review,
)

from app.events import (
    publish_review_created,
    subscribe_to_review_created,
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
    author_id: int

@strawberry.type
class Friend:
    id: strawberry.ID
    name: str
    
@strawberry.type
class HeroWithFriends:
    id: strawberry.ID
    name: str
    friends: list[Friend]
    
@strawberry.type
class DeleteReviewPayload:
    success: bool
    delete_review_id: strawberry.ID | None
    message: str
    
    
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
        
        
# ============================================================
# REVIEW QUERIES
# ============================================================

    @strawberry.field
    async def reviews(self) -> list[Review]:
        review_documents = await get_all_reviews()
        return [
            Review(
                id=document["id"],
                episode=Episode(document["episode"]),
                stars=document["stars"],
                commentary=document.get("commentary"),
                author_id=document["authorId"],
            )
            for document in review_documents
        ]
        
# ============================================================
# MUTATION ROOT
# ============================================================

@strawberry.type
class Mutation:

    @strawberry.mutation
    async def create_review(
        self,
        info: strawberry.Info,
        episode: Episode,
        review: ReviewInput,
    ) -> Review:
        authenticated_user = info.context["user"]

        saved_review = await create_review(
            episode=episode.value,
            stars=review.stars,
            commentary=review.commentary,
            author_id=authenticated_user["id"],
        )

        created_review = Review(
            id=saved_review["id"],
            episode=Episode(saved_review["episode"]),
            stars=saved_review["stars"],
            commentary=saved_review["commentary"],
            author_id=saved_review["authorId"],
        )

        await publish_review_created(saved_review)

        return created_review

    
    @strawberry.mutation
    async def update_my_nickname(
        self,
        info: strawberry.Info,
        nickname: str
    ) -> User:
        
        authenticated_user = info.context["user"]
        
        updated_user = await update_user_nickname(
            user_id=authenticated_user["id"],
            nickname=nickname
        )
        
        return User(
            id=updated_user["id"],
        )
        
    @strawberry.mutation
    async def delete_my_review(
        self,
        info: strawberry.Info,
        review_id: strawberry.ID,
    ) -> DeleteReviewPayload:
        
        authenticated_user = info.context["user"]

        deleted_review = await delete_review(
            review_id=str(review_id),
            author_id=authenticated_user["id"],
        )

        if deleted_review is None:
            return DeleteReviewPayload(
                success=False,
                delete_review_id=None,
                message="Review not found or not authorized to delete."
            )

        return DeleteReviewPayload(
            success=True,
            delete_review_id=review_id,
            message="Review successfully deleted."
        )
    
 
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
            yield Review(
                id=document["id"],
                episode=Episode(document["episode"]),
                stars=document["stars"],
                commentary=document.get("commentary"),
                author_id=document["authorId"],
            )
            
    
# ============================================================
# GRAPHQL SCHEMA
# ============================================================

schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    subscription=Subscription
)