from __future__ import annotations

from typing import Any


# Deterministic offline travel catalog. Estimates only — not live inventory.
CATALOG: dict[str, dict[str, Any]] = {
    "Goa": {
        "label": "Goa, India",
        "seasonal": "Peak dry season Nov–Mar; beaches and nightlife year-round with monsoon Jun–Sep.",
        "attractions": [
            {"name": "Calangute Beach", "area": "North Goa", "est_cost": 0},
            {"name": "Baga Beach", "area": "North Goa", "est_cost": 0},
            {"name": "Fort Aguada", "area": "North Goa", "est_cost": 50},
            {"name": "Basilica of Bom Jesus", "area": "Old Goa", "est_cost": 0},
            {"name": "Panaji Fontainhas", "area": "Panaji", "est_cost": 0},
            {"name": "Palolem Beach", "area": "South Goa", "est_cost": 0},
        ],
        "hotels": [
            {
                "name": "North Goa Mid-Range Stay",
                "area": "Calangute",
                "nights": 4,
                "nightly_inr": 2300,
                "total_inr": 9200,
                "provenance": "local-catalog-sample",
            },
            {
                "name": "Boutique Panaji Inn",
                "area": "Panaji",
                "nights": 4,
                "nightly_inr": 2800,
                "total_inr": 11200,
                "provenance": "local-catalog-sample",
            },
            {
                "name": "South Goa Quiet Resort",
                "area": "Palolem",
                "nights": 4,
                "nightly_inr": 2600,
                "total_inr": 10400,
                "provenance": "local-catalog-sample",
            },
        ],
        "transport": [
            {
                "mode": "flight",
                "label": "CCU → GOI round-trip (sample)",
                "total_inr": 12500,
                "provenance": "local-catalog-sample",
            },
            {
                "mode": "train+taxi",
                "label": "Train to Madgaon + local taxi (sample)",
                "total_inr": 7800,
                "provenance": "local-catalog-sample",
            },
        ],
        "coords": {"lat": 15.4909, "lng": 73.8278},
        "cover": "/assets/destinations/goa.jpg",
    },
    "Manali": {
        "label": "Manali, India",
        "seasonal": "Best Apr–Jun and Sep–Nov; snow Dec–Feb.",
        "attractions": [
            {"name": "Hadimba Temple", "area": "Old Manali", "est_cost": 50},
            {"name": "Solang Valley", "area": "Solang", "est_cost": 800},
            {"name": "Old Manali Cafes", "area": "Old Manali", "est_cost": 600},
        ],
        "hotels": [
            {
                "name": "Pine View Homestay",
                "area": "Manali",
                "nights": 5,
                "nightly_inr": 2200,
                "total_inr": 11000,
                "provenance": "local-catalog-sample",
            }
        ],
        "transport": [
            {
                "mode": "bus+taxi",
                "label": "Overnight bus + local taxi (sample)",
                "total_inr": 6500,
                "provenance": "local-catalog-sample",
            }
        ],
        "coords": {"lat": 32.2396, "lng": 77.1887},
        "cover": "/assets/destinations/manali.jpg",
    },
    "Jaipur": {
        "label": "Jaipur, India",
        "seasonal": "Best Oct–Mar; summers are hot.",
        "attractions": [
            {"name": "Amber Fort", "area": "Amer", "est_cost": 500},
            {"name": "City Palace", "area": "Pink City", "est_cost": 300},
            {"name": "Hawa Mahal", "area": "Pink City", "est_cost": 50},
        ],
        "hotels": [
            {
                "name": "Heritage Haveli Stay",
                "area": "Jaipur",
                "nights": 3,
                "nightly_inr": 3200,
                "total_inr": 9600,
                "provenance": "local-catalog-sample",
            }
        ],
        "transport": [
            {
                "mode": "flight",
                "label": "Round-trip flight sample",
                "total_inr": 9000,
                "provenance": "local-catalog-sample",
            }
        ],
        "coords": {"lat": 26.9124, "lng": 75.7873},
        "cover": "/assets/destinations/jaipur.jpg",
    },
    "Udaipur": {
        "label": "Udaipur, India",
        "seasonal": "Pleasant Sep–Mar; lakeside evenings.",
        "attractions": [
            {"name": "City Palace", "area": "Old City", "est_cost": 300},
            {"name": "Lake Pichola", "area": "Lakeside", "est_cost": 400},
        ],
        "hotels": [
            {
                "name": "Lakeview Heritage Hotel",
                "area": "Udaipur",
                "nights": 3,
                "nightly_inr": 3500,
                "total_inr": 10500,
                "provenance": "local-catalog-sample",
            }
        ],
        "transport": [
            {
                "mode": "flight",
                "label": "Round-trip flight sample",
                "total_inr": 11000,
                "provenance": "local-catalog-sample",
            }
        ],
        "coords": {"lat": 24.5854, "lng": 73.7125},
        "cover": "/assets/destinations/udaipur.jpg",
    },
    "Munnar": {
        "label": "Munnar, India",
        "seasonal": "Cool hills Sep–Mar; tea estates year-round.",
        "attractions": [
            {"name": "Tea Museum", "area": "Munnar", "est_cost": 125},
            {"name": "Eravikulam National Park", "area": "Munnar", "est_cost": 200},
        ],
        "hotels": [
            {
                "name": "Tea Estate Stay",
                "area": "Munnar",
                "nights": 3,
                "nightly_inr": 2800,
                "total_inr": 8400,
                "provenance": "local-catalog-sample",
            }
        ],
        "transport": [
            {
                "mode": "flight+taxi",
                "label": "Fly to COK + hill taxi (sample)",
                "total_inr": 14000,
                "provenance": "local-catalog-sample",
            }
        ],
        "coords": {"lat": 10.0889, "lng": 77.0595},
        "cover": "/assets/destinations/munnar.jpg",
    },
    "Kerala": {
        "label": "Kerala Backwaters, India",
        "seasonal": "Sep–Mar ideal for houseboats.",
        "attractions": [
            {"name": "Alleppey Houseboat", "area": "Alappuzha", "est_cost": 8000},
            {"name": "Village Walk", "area": "Backwaters", "est_cost": 300},
        ],
        "hotels": [
            {
                "name": "Backwater Resort",
                "area": "Alappuzha",
                "nights": 3,
                "nightly_inr": 4000,
                "total_inr": 12000,
                "provenance": "local-catalog-sample",
            }
        ],
        "transport": [
            {
                "mode": "flight",
                "label": "Round-trip to COK (sample)",
                "total_inr": 13000,
                "provenance": "local-catalog-sample",
            }
        ],
        "coords": {"lat": 9.4981, "lng": 76.3388},
        "cover": "/assets/destinations/kerala.jpg",
    },
    "Darjeeling": {
        "label": "Darjeeling, India",
        "seasonal": "Clear Himalayan views Oct–Nov and Mar–May; monsoon Jun–Sep.",
        "attractions": [
            {"name": "Tiger Hill Sunrise", "area": "Ghoom", "est_cost": 100},
            {"name": "Batasia Loop", "area": "Darjeeling", "est_cost": 50},
            {"name": "Happy Valley Tea Estate", "area": "Darjeeling", "est_cost": 200},
            {"name": "Himalayan Mountaineering Institute", "area": "Darjeeling", "est_cost": 150},
            {"name": "Toy Train Joyride", "area": "Darjeeling", "est_cost": 1500},
        ],
        "hotels": [
            {
                "name": "Tea Valley Homestay",
                "area": "Darjeeling",
                "nights": 3,
                "nightly_inr": 2600,
                "total_inr": 7800,
                "provenance": "local-catalog-sample",
            }
        ],
        "transport": [
            {
                "mode": "train+jeep",
                "label": "Sleeper to NJP + shared jeep, round-trip (sample)",
                "total_inr": 4200,
                "provenance": "local-catalog-sample",
            }
        ],
        "coords": {"lat": 27.0360, "lng": 88.2627},
        "cover": "/assets/destinations/darjeeling.jpg",
    },
    "Rishikesh": {
        "label": "Rishikesh, India",
        "seasonal": "Pleasant Sep–Nov and Feb–Apr; rafting closed Jul–Sep.",
        "attractions": [
            {"name": "Laxman Jhula", "area": "Tapovan", "est_cost": 0},
            {"name": "Triveni Ghat Ganga Aarti", "area": "Triveni Ghat", "est_cost": 0},
            {"name": "White-water Rafting", "area": "Shivpuri", "est_cost": 1500},
            {"name": "Morning Yoga Session", "area": "Tapovan", "est_cost": 600},
        ],
        "hotels": [
            {
                "name": "Riverside Yoga Retreat",
                "area": "Tapovan",
                "nights": 3,
                "nightly_inr": 3000,
                "total_inr": 9000,
                "provenance": "local-catalog-sample",
            }
        ],
        "transport": [
            {
                "mode": "flight+taxi",
                "label": "Fly to DED + taxi, round-trip (sample)",
                "total_inr": 13500,
                "provenance": "local-catalog-sample",
            }
        ],
        "coords": {"lat": 30.0869, "lng": 78.2676},
        "cover": "/assets/destinations/rishikesh.jpg",
    },
}


class TravelCatalogProvider:
    """Local deterministic catalog adapter — never claims live availability."""

    def lookup_destination(self, name: str) -> dict[str, Any]:
        key = self._normalize(name)
        if key in CATALOG:
            return {"key": key, **CATALOG[key]}
        # fuzzy contains
        for k, v in CATALOG.items():
            if k.lower() in name.lower() or name.lower() in k.lower():
                return {"key": k, **v}
        return {
            "key": key or "Unknown",
            "label": name or "Unknown destination",
            "seasonal": "Seasonal guidance unavailable for this destination in local catalog.",
            "attractions": [],
            "hotels": [],
            "transport": [],
            "coords": {},
            "cover": "/assets/destinations/generic.jpg",
        }

    def list_destinations(self) -> list[str]:
        return list(CATALOG.keys())

    def _normalize(self, name: str) -> str:
        raw = (name or "").strip()
        for k in CATALOG:
            if k.lower() == raw.lower() or k.lower() in raw.lower():
                return k
        return raw.split(",")[0].strip() if raw else "Unknown"


catalog_provider = TravelCatalogProvider()
