# GraphQL FastAPI Fundamentals Layer

A learning project that implements the concepts from the
[graphql.org **Learn**](https://graphql.org/learn/) section using
**FastAPI + Strawberry GraphQL + MongoDB (async PyMongo)**.

This is the *fundamentals layer*. The next stage refactors this project page by page
according to the graphql.org **Best Practices** section.

## Stack

| Layer      | Tool                                   |
|------------|----------------------------------------|
| HTTP / WS  | FastAPI + Uvicorn                      |
| GraphQL    | Strawberry (`strawberry-graphql[fastapi]`) |
| Database   | MongoDB via `pymongo.AsyncMongoClient` |
| Config     | `python-dotenv`                        |

## Project layout

```text
app/
  main.py      # FastAPI app, GraphQLRouter at /graphql, context (Bearer token -> user)
  schema.py    # All types, Query / Mutation / Subscription roots, schema object
  database.py  # MongoDB access: users + reviews collections
  events.py    # In-memory pub/sub (asyncio.Queue) used by subscriptions
  auth.py      # Standalone REST-style auth dependency (not wired into GraphQL)
seed.py        # Seeds one user with token "marwan-secret-token"
```

## What was covered (graphql.org/learn → code)

| Learn page | Where it lives in the code |
|---|---|
| **Schemas and Types**: object types, scalars, `ID`, nullability, lists | `User`, `Starship`, `Review`, `Friend`, `HeroWithFriends` |
| **Enums** | `Episode`, `LengthUnit` |
| **Arguments**, including default values | `Starship.length(unit: LengthUnit = METER)`, `droid(id: ID!)`, `search(text:)` |
| **Interfaces** | `Character` implemented by `Human` and `Droid`; `hero` / `humanHero` return `Character` |
| **Union types** | `SearchResult = Human \| Droid \| Starship` returned by `search` |
| **Input types** | `ReviewInput` used by `createReview` |
| **Queries**: fields, nested lists, aliases, fragments, inline fragments, variables, `__typename` | `hero`, `heroWithFriends`, `search`, `reviews` (client-side query features run against these) |
| **Mutations**: create / update / delete, payload types | `createReview`, `updateMyNickname`, `deleteMyReview` → `DeleteReviewPayload` |
| **Subscriptions** | `count(target)` (a simple stream), `reviewCreated` (pushed when `createReview` runs) |
| **Execution / resolvers**: async resolvers, per-field DB lookups, the `info.context` | `User.fullName` / `User.nickname` resolve from MongoDB; `me` reads `info.context["user"]` |
| **Deprecation** | `User.name` → `deprecation_reason="Use fullName."` |
| **Hidden internal fields** | `Starship.length_in_meters: strawberry.Private[float]` |
| **Introspection** | Built-in; available in GraphiQL at `/graphql` |
| **Authentication via context** | `main.get_context` reads `Authorization: Bearer <token>` and looks up the user |

### Known gaps (to fix in the Best Practices stage)

- Mutations assume an authenticated user. A missing token returns a leaked internal `TypeError` message instead of a clear authentication error.
- `User` fields each hit the DB separately (N+1). DataLoaders are not used yet.
- No pagination on `reviews`. No validation on `stars`.
- Star Wars data is hard-coded in `schema.py`. Everything sits in a single schema file.
- Pub/sub is in-memory only, so it only works within a single process.

## Running locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # requires a local MongoDB on :27017
python seed.py
uvicorn app.main:app --reload
```

Open <http://localhost:8000/graphql> (GraphiQL). For authenticated operations, add this header:

```json
{ "Authorization": "Bearer marwan-secret-token" }
```

### Sample operations

```graphql
query { me { id fullName nickname name } }

query Search($text: String!) {
  search(text: $text) {
    __typename
    ... on Character { id name }
    ... on Human { height }
    ... on Droid { primaryFunction }
    ... on Starship { feet: length(unit: FOOT) }
  }
}

mutation {
  createReview(episode: JEDI, review: { stars: 5, commentary: "Great!" }) {
    id episode stars commentary authorId
  }
}

subscription { reviewCreated { id episode stars } }
```
