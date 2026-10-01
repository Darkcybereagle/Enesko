import re
import unicodedata
from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import KnowledgeDocument, Store


STOP_WORDS = {
    "where", "what", "which", "with", "from", "that", "this", "there",
    "about", "could", "would", "please", "mall", "find", "store", "shop",
    "want", "need", "have", "does", "your", "their", "right", "now", "can", "buy",
    "take", "navigate", "navigation", "direction", "directions", "get",
    "nibo", "ibo", "ninu", "fun", "pelu", "lati", "si", "ni", "wa", "mo", "fe",
    "je", "se", "ki", "mi", "yin", "re",
}


def _fold_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in normalized if not unicodedata.combining(char))

SEARCH_SYNONYMS = {
    "shoe": {"footwear", "sneaker", "trainer"},
    "shoes": {"footwear", "sneakers", "trainers"},
    "sneaker": {"shoe", "footwear", "trainer"},
    "sneakers": {"shoes", "footwear", "trainers"},
    "trainer": {"shoe", "footwear", "sneaker"},
    "trainers": {"shoes", "footwear", "sneakers"},
    "sport": {"sports", "fitness"},
    "sports": {"sport", "fitness"},
    "phone": {"phones", "smartphone", "mobile"},
    "phones": {"phone", "smartphones", "mobile"},
    "clothes": {"clothing", "apparel", "fashion"},
    "clothing": {"clothes", "apparel", "fashion"},
    "eat": {"food", "restaurant", "dining", "meal", "meals"},
    "food": {"restaurant", "dining", "meal", "meals"},
    "meal": {"food", "restaurant", "dining"},
    "meals": {"food", "restaurant", "dining"},
    "water": {"drink", "drinks", "beverage", "beverages", "groceries", "supermarket"},
    "drink": {"drinks", "beverage", "beverages", "groceries"},
    "drinks": {"drink", "beverage", "beverages", "groceries"},
    "medicine": {"pharmacy", "health", "medicines"},
    "medicines": {"pharmacy", "health", "medicine"},
    "perfume": {"fragrance", "beauty"},
    "fragrance": {"perfume", "beauty"},
    "makeup": {"cosmetics", "beauty"},
    "cosmetics": {"makeup", "beauty"},
    "watch": {"watches", "accessories"},
    "watches": {"watch", "accessories"},
    "gift": {"gifts", "lifestyle"},
    "gifts": {"gift", "lifestyle"},
}


def _tokens(text: str, min_len: int = 3) -> list[str]:
    return [
        token for token in re.findall(r"[a-z0-9]+", _fold_text(text))
        if len(token) >= min_len and token not in STOP_WORDS
    ]


def search_stores(db: Session, query: str) -> list[Store]:
    now = datetime.utcnow()
    stores = list(
        db.scalars(
            select(Store)
            .options(selectinload(Store.categories))
            .where(
                Store.active.is_(True),
                or_(Store.expires_at.is_(None), Store.expires_at >= now),
            )
            .order_by(Store.name)
        ).unique().all()
    )
    tokens = _tokens(query)

    expanded_terms: dict[str, set[str]] = {
        token: {token, *SEARCH_SYNONYMS.get(token, set())}
        for token in tokens
    }

    def score(store: Store) -> int:
        name = (store.name or "").lower()
        description = (store.description or "").lower()
        landmark = (store.nearest_landmark or "").lower()
        categories = " ".join(category.name for category in store.categories).lower()
        haystack = " ".join([name, description, landmark, categories])

        points = 0
        for token, terms in expanded_terms.items():
            direct_match = token in haystack
            synonym_match = any(term in haystack for term in terms if term != token)

            if token in name:
                points += 4
            elif direct_match:
                points += 2

            if synonym_match:
                points += 2

        return points

    ranked = sorted(
        ((score(store), store) for store in stores),
        key=lambda item: (-item[0], -item[1].discovery_priority, item[1].name),
    )
    return [store for points, store in ranked if points > 0][:5]


def _shopping_need_clauses(message: str) -> list[str]:
    folded = _fold_text(message)
    parts = re.split(r"\b(?:and|then|also|plus|after that|next)\b|[,;]", folded)
    cleaned: list[str] = []
    for part in parts:
        clause = re.sub(
            r"\b(?:i|we|want|need|would like|like|to|buy|get|find|where can|where do|please|can you)\b",
            " ",
            part,
        )
        clause = " ".join(clause.split()).strip(" .?!")
        if len(_tokens(clause, min_len=2)) == 0:
            continue
        if clause not in cleaned:
            cleaned.append(clause)
    return cleaned[:6]


def _store_payload(store: Store) -> dict:
    return {
        "id": store.id,
        "name": store.name,
        "unit": store.unit,
        "floor_id": store.floor_id,
        "zone_id": store.zone_id,
        "nearest_landmark": store.nearest_landmark,
        "opening_hours": store.opening_hours,
        "categories": [category.name for category in store.categories],
        "data_status": store.data_status,
        "source_name": store.source_name,
        "verified_at": store.verified_at,
        "expires_at": store.expires_at,
        "map_node_code": store.map_node_code,
        "verification_confidence": store.verification_confidence,
        "location_confidence": store.location_confidence,
    }


def _route_distance(db: Session, start_code: str, end_code: str) -> float | None:
    from app.phase4 import calculate_route

    try:
        return calculate_route(
            db,
            start_code,
            end_code,
            accessible_only=True,
        )["total_distance_m"]
    except Exception:
        return None


def build_shopping_plan(db: Session, message: str) -> dict | None:
    needs = _shopping_need_clauses(message)
    if len(needs) < 2:
        return None

    plan = []
    for need in needs:
        stores = search_stores(db, need)
        if not stores:
            plan.append(
                {
                    "need": need,
                    "recommended_store": None,
                    "alternatives": [],
                    "proximity_status": "NO_MATCH",
                    "distance_from_start_m": None,
                }
            )
            continue

        candidates = stores[:4]
        recommended = candidates[0]
        mapped_candidates = [store for store in candidates if store.map_node_code]
        mapped_with_distance = []
        for store in mapped_candidates:
            distance = _route_distance(db, "ICM-ENTRANCE-2", store.map_node_code)
            if distance is not None:
                mapped_with_distance.append((distance, store))

        proximity_status = "CATALOG_ONLY"
        distance_from_start = None
        if recommended.map_node_code:
            distance_from_start = _route_distance(
                db,
                "ICM-ENTRANCE-2",
                recommended.map_node_code,
            )
            if distance_from_start is not None:
                proximity_status = "ROUTE_VERIFIED_REFERENCE"
        elif mapped_with_distance:
            proximity_status = "RELEVANCE_FIRST_PARTIAL_MAP"

        plan.append(
            {
                "need": need,
                "recommended_store": _store_payload(recommended),
                "alternatives": [
                    _store_payload(store)
                    for store in candidates[1:]
                ],
                "proximity_status": proximity_status,
                "distance_from_start_m": distance_from_start,
            }
        )

    if sum(1 for item in plan if item["recommended_store"]) < 2:
        return None

    mapped_stops = [
        item
        for item in plan
        if item["recommended_store"]
        and item["recommended_store"]["map_node_code"]
    ]
    remaining = list(mapped_stops)
    ordered_mapped = []
    current_node = "ICM-ENTRANCE-2"

    while remaining:
        ranked_next = []
        for item in remaining:
            target_node = item["recommended_store"]["map_node_code"]
            distance = _route_distance(db, current_node, target_node)
            if distance is not None:
                ranked_next.append((distance, item))

        if not ranked_next:
            break

        ranked_next.sort(key=lambda pair: pair[0])
        distance, selected = ranked_next[0]
        selected["distance_from_previous_m"] = distance
        selected["route_from_node"] = current_node
        ordered_mapped.append(selected)
        current_node = selected["recommended_store"]["map_node_code"]
        remaining.remove(selected)

    mapped_without_route = [item for item in mapped_stops if item not in ordered_mapped]
    unmapped_stops = [
        item
        for item in plan
        if item["recommended_store"]
        and not item["recommended_store"]["map_node_code"]
    ]
    unresolved = [item for item in plan if not item["recommended_store"]]

    ordered = ordered_mapped + mapped_without_route + unmapped_stops + unresolved
    for index, item in enumerate(ordered, start=1):
        item["suggested_order"] = index

    exact_proximity = (
        len(mapped_without_route) == 0
        and len(unmapped_stops) == 0
        and len(unresolved) == 0
    )
    return {
        "needs": ordered,
        "start_node": "ICM-ENTRANCE-2",
        "proximity_basis": (
            "REFERENCE_ROUTE_DISTANCE"
            if exact_proximity
            else "PARTIAL_REFERENCE_ROUTE_PLUS_RELEVANCE"
        ),
        "exact_proximity_order": exact_proximity,
    }


def find_knowledge(db: Session, query: str) -> list[KnowledgeDocument]:
    tokens = _tokens(query, min_len=4)
    if not tokens:
        return []

    clauses = []
    for token in tokens[:8]:
        pattern = f"%{token}%"
        clauses.extend([
            KnowledgeDocument.title.ilike(pattern),
            KnowledgeDocument.content.ilike(pattern),
        ])

    docs = list(
        db.scalars(
            select(KnowledgeDocument)
            .where(KnowledgeDocument.verified.is_(True), or_(*clauses))
            .order_by(KnowledgeDocument.updated_at.desc())
            .limit(5)
        ).all()
    )
    now = datetime.utcnow()
    return [doc for doc in docs if doc.expires_at is None or doc.expires_at >= now]


YORUBA_MARKERS = {
    "nibo", "ibo", "bata", "foonu", "ounje", "sinima", "fiimu", "paaki",
    "padanu", "sonu", "soobu", "iranlowo", "dari", "oko", "ra",
}


def detect_language(message: str) -> str:
    raw = message.lower()
    folded = _fold_text(message)
    tokens = set(re.findall(r"[a-z0-9]+", folded))
    if any(char in raw for char in ("ẹ", "ọ", "ṣ")):
        return "yo-NG"
    if tokens.intersection(YORUBA_MARKERS):
        return "yo-NG"
    if any(
        phrase in folded
        for phrase in (
            "mo fe", "mu mi lo si", "dari mi lo si", "ona si",
            "nibo ni", "ibo ni", "mo padanu", "mo sonu",
        )
    ):
        return "yo-NG"
    return "en-NG"


def classify_intent(message: str) -> str:
    text = _fold_text(message)
    if any(term in text for term in (
        "human", "customer care", "customer service", "speak to someone", "agent",
        "iranlowo eniyan", "ba eniyan soro", "so mi po mo eniyan",
    )):
        return "human_handoff"
    if any(term in text for term in ("lost", "missing", "misplaced", "padanu", "sonu")):
        return "lost_found"
    if any(term in text for term in ("movie", "cinema", "showtime", "film showing", "films showing", "sinima", "fiimu")):
        return "cinema"
    if any(term in text for term in ("parking", "park my car", "parking space", "paaki", "ibi idako", "pa oko")):
        return "parking"
    if any(term in text for term in (
        "take me to", "navigate to", "directions to", "how do i get to", "guide me to",
        "mu mi lo si", "dari mi lo si", "ona si",
    )):
        return "navigation"
    if len(_shopping_need_clauses(message)) >= 2 and any(
        term in text
        for term in (
            "buy", "get", "eat", "food", "water", "drink", "shoe", "shoes",
            "medicine", "perfume", "makeup", "phone", "clothes", "gift",
        )
    ):
        return "shopping_plan"
    if any(term in text for term in (
        "where is", "where can i", "find", "buy", "store", "shop", "restaurant",
        "nibo ni", "ibo ni", "ra", "soobu", "ounje",
    )):
        return "store_search"
    return "knowledge_query"


def _orchestrate_base(db: Session, message: str) -> dict:
    intent = classify_intent(message)

    if intent == "shopping_plan":
        plan = build_shopping_plan(db, message)
        if plan:
            need_lines = []
            for item in plan["needs"]:
                order = item.get("suggested_order")
                store = item["recommended_store"]
                if not store:
                    need_lines.append(
                        f"Stop {order}: for {item['need']}, I do not yet have a verified matching store."
                    )
                    continue

                alternatives = item["alternatives"]
                line = f"Stop {order}: for {item['need']}, I recommend {store['name']}"
                if alternatives:
                    names = ", ".join(option["name"] for option in alternatives)
                    line += f"; other matching options are {names}"
                if item.get("distance_from_previous_m") is not None:
                    line += (
                        f". This mapped leg is about {item['distance_from_previous_m']:.0f} metres "
                        "on the current ENESKO reference route"
                    )
                line += "."
                need_lines.append(line)

            if plan["exact_proximity_order"]:
                order_note = (
                    "I ordered these stops using the current ENESKO reference-route distances "
                    "from Entrance 2."
                )
            else:
                order_note = (
                    "I can suggest the shopping sequence, but some recommended stores are not yet "
                    "mapped precisely enough for a fully verified proximity order. Mapped stops are "
                    "ordered by ENESKO reference-route distance; unmapped stops remain relevance-based."
                )

            return {
                "answer": " ".join(need_lines) + " " + order_note,
                "intent": intent,
                "needs_human": False,
                "sources": [],
                "data": {"shopping_plan": plan},
            }

    if intent == "human_handoff":
        return {
            "answer": "I can create a support case for mall operations so a human team member can follow up.",
            "intent": intent,
            "needs_human": True,
            "sources": [],
            "data": {"workflow": "customer_assistance"},
        }

    if intent == "lost_found":
        return {
            "answer": (
                "I can start a lost-and-found case. Tell me the item, colour or identifying features, "
                "where you last saw it, the approximate time and a contact method. Mall staff must verify "
                "any match before an item can be released."
            ),
            "intent": intent,
            "needs_human": True,
            "sources": [],
            "data": {"workflow": "lost_found_intake"},
        }

    if intent == "cinema":
        from app.phase9 import CinemaShow

        now = datetime.utcnow()
        shows = list(
            db.scalars(
                select(CinemaShow)
                .where(or_(CinemaShow.expires_at.is_(None), CinemaShow.expires_at >= now))
                .order_by(CinemaShow.id)
                .limit(8)
            ).all()
        )

        if shows:
            summary = "; ".join(f"{show.movie_title}: {show.show_time}" for show in shows[:4])
            return {
                "answer": (
                    "Here are the current cinema records available to ENESKO: "
                    f"{summary}. Use the official booking service to confirm seats and final availability."
                ),
                "intent": intent,
                "needs_human": False,
                "sources": [
                    {
                        "title": show.movie_title,
                        "source_name": show.source,
                        "updated_at": show.verified_at or now,
                        "expires_at": show.expires_at,
                    }
                    for show in shows[:4]
                ],
                "data": {
                    "cinema_name": "Silverbird Cinemas, Ikeja City Mall",
                    "movie_enquiry": "+234 902 606 7603",
                    "official_booking_url": "https://silverbirdcinemas.com/cinema/ikeja/",
                    "shows": [
                        {
                            "movie_title": show.movie_title,
                            "show_time": show.show_time,
                            "data_status": show.data_status,
                            "source": show.source,
                        }
                        for show in shows
                    ],
                },
            }

        return {
            "answer": (
                "Silverbird Cinemas operates at Ikeja City Mall, but ENESKO has no fresh showtime "
                "record at the moment. I will not invent a schedule. Use the official booking service "
                "for current listings."
            ),
            "intent": intent,
            "needs_human": False,
            "sources": [],
            "data": {
                "cinema_name": "Silverbird Cinemas, Ikeja City Mall",
                "movie_enquiry": "+234 902 606 7603",
                "official_booking_url": "https://silverbirdcinemas.com/cinema/ikeja/",
                "shows": [],
            },
        }

    if intent == "parking":
        from app.phase10 import ParkingStatus

        row = db.scalar(select(ParkingStatus).order_by(ParkingStatus.id))
        now = datetime.utcnow()
        fresh_staff_status = (
            row is not None
            and row.data_status == "STAFF_VERIFIED"
            and row.expires_at is not None
            and row.expires_at >= now
        )

        if fresh_staff_status:
            readable = row.occupancy_status.replace("_", " ").title()
            return {
                "answer": (
                    f"The current staff-verified parking status is {readable}. "
                    "Ikeja City Mall also publishes that it has more than 700 parking bays."
                ),
                "intent": intent,
                "needs_human": False,
                "sources": [],
                "data": {
                    "area_code": row.area_code,
                    "status": row.occupancy_status,
                    "verified_until": row.expires_at,
                    "published_capacity": "700+ bays",
                },
            }

        return {
            "answer": (
                "Ikeja City Mall publishes that it has more than 700 parking bays, but ENESKO does not "
                "currently have a fresh verified live occupancy status. I will not guess whether spaces "
                "are available right now."
            ),
            "intent": intent,
            "needs_human": False,
            "sources": [],
            "data": {
                "published_capacity": "700+ bays",
                "live_status": "UNAVAILABLE",
            },
        }

    if intent == "navigation":
        stores = search_stores(db, message)
        mapped = next((store for store in stores if store.map_node_code), None)
        if mapped:
            from app.phase4 import calculate_route

            route = calculate_route(
                db,
                "ICM-ENTRANCE-2",
                mapped.map_node_code,
                accessible_only=True,
            )
            spoken_steps = " ".join(step["instruction"] for step in route["steps"])
            return {
                "answer": (
                    f"I found {mapped.name}. Starting from Entrance 2: {spoken_steps} "
                    "The current path is an ENESKO reference route until the authorized mall floor plan is connected."
                ),
                "intent": intent,
                "needs_human": False,
                "sources": [],
                "data": {
                    "store": {
                        "id": mapped.id,
                        "name": mapped.name,
                        "map_node_code": mapped.map_node_code,
                        "data_status": mapped.data_status,
                    },
                    "route": route,
                },
            }

        return {
            "answer": (
                "I found matching store information, but that destination does not yet have an ENESKO indoor-map node. "
                "I will not invent a route."
            ),
            "intent": intent,
            "needs_human": False,
            "sources": [],
            "data": {
                "stores": [
                    {
                        "id": store.id,
                        "name": store.name,
                        "map_node_code": store.map_node_code,
                        "data_status": store.data_status,
                    }
                    for store in stores
                ]
            },
        }

    if intent == "store_search":
        stores = search_stores(db, message)
        if stores:
            first = stores[0]
            answer = f"I found {first.name}"
            if first.nearest_landmark:
                answer += f", near {first.nearest_landmark}"
            answer += "."
            if first.data_status == "PUBLIC_VERIFIED":
                answer += " This listing comes from a currently verified public directory source."
            if first.map_node_code:
                answer += " An ENESKO indoor navigation reference route is available for this location."

            return {
                "answer": answer,
                "intent": intent,
                "needs_human": False,
                "sources": [],
                "data": {
                    "stores": [
                        {
                            "id": store.id,
                            "name": store.name,
                            "unit": store.unit,
                            "floor_id": store.floor_id,
                            "zone_id": store.zone_id,
                            "nearest_landmark": store.nearest_landmark,
                            "opening_hours": store.opening_hours,
                            "categories": [c.name for c in store.categories],
                            "data_status": store.data_status,
                            "source_name": store.source_name,
                            "verified_at": store.verified_at,
                            "expires_at": store.expires_at,
                            "map_node_code": store.map_node_code,
                        }
                        for store in stores
                    ]
                },
            }

    docs = find_knowledge(db, message)
    if docs:
        doc = docs[0]
        excerpt = " ".join(doc.content.split())
        if len(excerpt) > 700:
            excerpt = excerpt[:697] + "..."
        return {
            "answer": excerpt,
            "intent": "knowledge_query",
            "needs_human": False,
            "sources": [
                {
                    "title": item.title,
                    "source_name": item.source_name,
                    "updated_at": item.updated_at,
                    "expires_at": item.expires_at,
                }
                for item in docs
            ],
            "data": None,
        }

    return {
        "answer": (
            "I do not have a current verified source for that information, so I will not guess. "
            "You can ask ENESKO to create a support case or connect an approved data source."
        ),
        "intent": "unknown",
        "needs_human": True,
        "sources": [],
        "data": None,
    }



def _localize_yoruba(result: dict) -> dict:
    intent = result.get("intent", "unknown")
    data = result.get("data") or {}

    if intent == "human_handoff":
        answer = (
            "Mo lè dá ìbéèrè ìrànlọ́wọ́ sílẹ̀ fún ẹgbẹ́ iṣẹ́ Ikeja City Mall "
            "kí òṣìṣẹ́ ènìyàn lè tẹ̀síwájú pẹ̀lú rẹ."
        )
    elif intent == "lost_found":
        answer = (
            "Mo lè bẹ̀rẹ̀ ìròyìn nkan tí ó sọnù. Sọ ohun tí ó sọnù, àwọ̀ tàbí àmì rẹ, "
            "ibi tí o ti rí i kẹ́yìn, àkókò tó ṣẹlẹ̀ àti ọ̀nà ìbánisọ̀rọ̀. "
            "Òṣìṣẹ́ mall gbọdọ̀ jẹ́rìí ohun náà kí wọ́n tó fi í sílẹ̀."
        )
    elif intent == "parking":
        status = data.get("status")
        if status:
            readable = str(status).replace("_", " ").title()
            answer = (
                f"Ipo ibi ìdákọ̀ ọkọ tí òṣìṣẹ́ fọwọ́sí báyìí ni {readable}. "
                "Ikeja City Mall tún sọ pé ó ní ju ibi ìdákọ̀ ọkọ 700 lọ."
            )
        else:
            answer = (
                "Ikeja City Mall sọ pé ó ní ju ibi ìdákọ̀ ọkọ 700 lọ, ṣùgbọ́n ENESKO "
                "kò ní ipo ìdákọ̀ ọkọ tuntun tí a fọwọ́sí ní báyìí. Mi ò ní ṣe àfojúsùn."
            )
    elif intent == "cinema":
        shows = data.get("shows") or []
        if shows:
            summary = "; ".join(
                f"{show.get('movie_title')}: {show.get('show_time')}"
                for show in shows[:4]
            )
            answer = (
                f"Àwọn ìfihàn sinimá tí ENESKO ní báyìí ni: {summary}. "
                "Jọ̀wọ́ lo iṣẹ́ ìfipamọ́ Silverbird láti jẹ́rìí ijoko àti àkókò ikẹhin."
            )
        else:
            answer = (
                "Silverbird Cinemas wà ní Ikeja City Mall, ṣùgbọ́n ENESKO kò ní "
                "àkókò ìfihàn tuntun tí a fọwọ́sí ní báyìí. Mi ò ní dá àkókò sílẹ̀ láìsí ẹ̀rí."
            )
    elif intent == "navigation":
        store = data.get("store") or {}
        route = data.get("route") or {}
        name = store.get("name")
        if name and route:
            answer = (
                f"Mo ti rí {name}. Bẹ̀rẹ̀ láti Entrance 2 kí o sì tẹ̀lé ipa-ọ̀nà ENESKO "
                "tí ó hàn lórí iboju. Ọ̀nà yìí ṣì jẹ́ reference route títí tí a ó fi "
                "gba floor plan Ikeja City Mall tí a fọwọ́sí."
            )
        else:
            answer = (
                "Mo rí ìtàn ibi náà, ṣùgbọ́n ibi náà kò tíì ní node maapu ENESKO. "
                "Mi ò ní dá ọ̀nà tí a kò fọwọ́sí sílẹ̀."
            )
    elif intent == "shopping_plan":
        plan = data.get("shopping_plan") or {}
        items = plan.get("needs") or []
        pieces = []
        for item in items:
            store = item.get("recommended_store")
            if store:
                pieces.append(
                    f"Fún {item.get('need')}, mo ṣeduro {store.get('name')}."
                )
            else:
                pieces.append(
                    f"Fún {item.get('need')}, mi ò tíì ní ṣọ́ọ̀bù tí a fọwọ́sí."
                )
        if plan.get("exact_proximity_order"):
            pieces.append(
                "Mo ṣètò àwọn ibi náà gẹ́gẹ́ bí ìjìnnà reference route láti Entrance 2."
            )
        else:
            pieces.append(
                "Diẹ̀ ninu àwọn ibi náà kò tíì ni maapu pipe, nítorí náà mo lo ipa-ọ̀nà "
                "reference fún àwọn tí a ti map, mo sì lo ibamu ọja fún àwọn iyókù."
            )
        answer = " ".join(pieces)
    elif intent == "store_search":
        stores = data.get("stores") or []
        if stores:
            first = stores[0]
            answer = f"Mo rí {first.get('name')}."
            if first.get("unit"):
                answer += f" Unit rẹ̀ ni {first.get('unit')}."
            if first.get("nearest_landmark"):
                answer += f" Ó wà nítòsí {first.get('nearest_landmark')}."
            if first.get("map_node_code"):
                answer += " ENESKO ní reference route sí ibi yìí."
        else:
            answer = "Mi ò rí ṣọ́ọ̀bù tó bá ìbéèrè yẹn mu nínú data tí a fọwọ́sí."
    elif intent == "knowledge_query" and result.get("answer"):
        answer = (
            "Mo rí ìmọ̀ tí a fọwọ́sí lórí ìbéèrè yìí. "
            f"Àkọsílẹ̀ orísun ni: {result['answer']}"
        )
    else:
        answer = (
            "Mi ò ní orísun tuntun tí a fọwọ́sí fún ìbéèrè yẹn, nítorí náà mi ò ní ṣe àfojúsùn. "
            "O lè ní kí ENESKO dá ìbéèrè ìrànlọ́wọ́ sílẹ̀ fún ẹgbẹ́ mall."
        )

    localized = dict(result)
    localized["answer"] = answer
    localized["language"] = "yo-NG"
    return localized


def orchestrate(db: Session, message: str) -> dict:
    language = detect_language(message)
    result = _orchestrate_base(db, message)
    if language == "yo-NG":
        return _localize_yoruba(result)

    result = dict(result)
    result["language"] = "en-NG"
    return result
