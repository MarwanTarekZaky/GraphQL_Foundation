"""A tiny normalized client cache, like the ones Apollo Client and Relay keep.

Every object that has an `id` is stored once, under that id. Query results
only keep references, so new data from ANY response shows up everywhere.

Run it while the server is running:  python cache_demo.py
"""

import json
import urllib.request


URL = "http://127.0.0.1:8000/graphql"
TOKEN = "marwan-secret-token"

cache: dict[str, dict] = {}


def graphql(query: str) -> dict:
    request = urllib.request.Request(
        URL,
        data=json.dumps({"query": query}).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {TOKEN}",
        },
    )

    with urllib.request.urlopen(request) as response:
        return json.load(response)["data"]


def normalize(value):
    """Store each object with an id in the cache and return a reference to it."""
    if isinstance(value, list):
        return [normalize(item) for item in value]

    if not isinstance(value, dict):
        return value

    fields = {key: normalize(item) for key, item in value.items()}

    if "id" not in fields:
        return fields

    cache.setdefault(fields["id"], {}).update(fields)

    # Remember which fields this query selected, so reading it back
    # returns exactly that shape (and never loops through user <-> review).
    return {"__ref": fields["id"], "__fields": list(fields)}


def read(value):
    """Rebuild a query result from the cache by following the references."""
    if isinstance(value, list):
        return [read(item) for item in value]

    if not isinstance(value, dict):
        return value

    if "__ref" in value:
        entry = cache[value["__ref"]]
        return {key: read(entry[key]) for key in value["__fields"]}

    return {key: read(item) for key, item in value.items()}


def show(title: str, profile, my_reviews):
    me = read(profile)["me"]
    authors = {review["author"]["nickname"] for review in read(my_reviews)["me"]["reviewsConnection"]["nodes"]}
    print(f"{title}\n  profile screen : {me['nickname']}\n  reviews screen : {authors}\n")


# Make sure there is at least one review by me to show.
graphql('mutation { addReview(input: { episode: JEDI, stars: 5, commentary: "cache demo" }) { review { id } } }')

# Two different "screens" fetch overlapping data with two different queries.
profile = normalize(graphql("{ me { id nickname } }"))
my_reviews = normalize(graphql("{ me { id reviewsConnection(first: 3) { nodes { id stars author { id nickname } } } } }"))

original = read(profile)["me"]["nickname"]
print(f"The cache holds {len(cache)} objects, and the user is stored once under {read(profile)['me']['id']!r}.\n")
show("1) After the two queries", profile, my_reviews)

# A mutation that selects `id`: the cache merges it into the existing user.
normalize(graphql('mutation { updateMyNickname(nickname: "Cached") { id nickname } }'))
show("2) After updateMyNickname { id nickname }  (no refetch)", profile, my_reviews)

# A mutation WITHOUT `id`: the cache can't tell which object changed.
normalize(graphql('mutation { updateMyNickname(nickname: "Stale?") { nickname } }'))
show("3) After updateMyNickname { nickname }  (no id selected)", profile, my_reviews)

graphql(f'mutation {{ updateMyNickname(nickname: "{original}") {{ id }} }}')
print(f"(nickname restored to {original!r})")
