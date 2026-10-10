"""
Seed dataset for SmartRail Railway Food Ordering System.
Provides realistic, high-quality demo restaurants and categorized railway meals
mapped to verified station junctions (NDLS, MMCT, JP, KOTA, RTM, BRC, ST, AII).
All vendors are labeled as verified IRCTC on-board partner vendors.
"""

DEMO_RESTAURANTS = [
    # New Delhi (NDLS)
    {
        "station_code": "NDLS",
        "name": "IRCTC Executive Food Plaza - New Delhi",
        "description": "Multi-cuisine IRCTC authorized rail food plaza serving hygienically packed fresh thalis, combos, and quick snacks.",
        "cuisine": "North Indian • South Indian • Chinese",
        "rating": 4.5,
        "image_url": "https://images.unsplash.com/photo-1585937421612-70a008356fbe?w=600&auto=format&fit=crop&q=80",
        "prep_time": "15-20 min",
        "min_order": 100.0,
        "is_veg_only": 0
    },
    {
        "station_code": "NDLS",
        "name": "Haldiram's Express - NDLS Concourse",
        "description": "Pure vegetarian specialty meals, royal Rajasthani & North Indian thalis, traditional chaat, and festive sweets.",
        "cuisine": "Pure Veg • North Indian • Sweets",
        "rating": 4.7,
        "image_url": "https://images.unsplash.com/photo-1546833999-b9f581a1996d?w=600&auto=format&fit=crop&q=80",
        "prep_time": "20-25 min",
        "min_order": 120.0,
        "is_veg_only": 1
    },
    {
        "station_code": "NDLS",
        "name": "Chai Point & Station Bites",
        "description": "Premium brewed filter coffee, kulhad masala chai, breakfast combos, samosas, and fresh sandwiches.",
        "cuisine": "Beverages • Breakfast • Fast Food",
        "rating": 4.3,
        "image_url": "https://images.unsplash.com/photo-1576092768241-dec231879fc3?w=600&auto=format&fit=crop&q=80",
        "prep_time": "10-15 min",
        "min_order": 50.0,
        "is_veg_only": 0
    },

    # Jaipur Junction (JP)
    {
        "station_code": "JP",
        "name": "Rawat Mishtan On-Track - Jaipur",
        "description": "Famous authentic Jaipur Pyaaz Kachori, Mawa Kachori, Rajasthani Dal Baati Churma, and fresh snacks.",
        "cuisine": "Rajasthani • Pure Veg • Snacks",
        "rating": 4.8,
        "image_url": "https://images.unsplash.com/photo-1601050690597-df0568f70950?w=600&auto=format&fit=crop&q=80",
        "prep_time": "15-20 min",
        "min_order": 80.0,
        "is_veg_only": 1
    },
    {
        "station_code": "JP",
        "name": "IRCTC Jan Aahaar - Jaipur Central",
        "description": "Government authorized budget-friendly nutritious meals, combo boxes, and regional thalis.",
        "cuisine": "North Indian • Budget Thali",
        "rating": 4.2,
        "image_url": "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=600&auto=format&fit=crop&q=80",
        "prep_time": "15-20 min",
        "min_order": 70.0,
        "is_veg_only": 0
    },

    # Kota Junction (KOTA)
    {
        "station_code": "KOTA",
        "name": "IRCTC Food Plaza - Kota Junction",
        "description": "Hot delivered meals packed in tamper-proof thermal boxes for Rajdhani and express trains halting at Kota.",
        "cuisine": "North Indian • South Indian • Combos",
        "rating": 4.4,
        "image_url": "https://images.unsplash.com/photo-1589302168068-964664d93dc0?w=600&auto=format&fit=crop&q=80",
        "prep_time": "20-25 min",
        "min_order": 100.0,
        "is_veg_only": 0
    },
    {
        "station_code": "KOTA",
        "name": "Bikanervala Station Bites - Kota",
        "description": "Pure vegetarian delight with special Jain thalis, paneer specialties, lassi, and fresh sweets.",
        "cuisine": "Pure Veg • Thali • Snacks",
        "rating": 4.6,
        "image_url": "https://images.unsplash.com/photo-1546833999-b9f581a1996d?w=600&auto=format&fit=crop&q=80",
        "prep_time": "15-20 min",
        "min_order": 120.0,
        "is_veg_only": 1
    },

    # Ratlam Junction (RTM)
    {
        "station_code": "RTM",
        "name": "Ratlam Junction Rail Rasoi",
        "description": "Home of world-famous Ratlami Sev, crispy Poha, Malwi Dal Bafla, and comforting homestyle thalis.",
        "cuisine": "Malwi • North Indian • Thali",
        "rating": 4.7,
        "image_url": "https://images.unsplash.com/photo-1565299585323-38d6b0865b47?w=600&auto=format&fit=crop&q=80",
        "prep_time": "15-20 min",
        "min_order": 80.0,
        "is_veg_only": 1
    },
    {
        "station_code": "RTM",
        "name": "Comsomb Caterers - Ratlam",
        "description": "Reliable on-train caterer offering aromatic chicken biryani, paneer butter masala, and paratha rolls.",
        "cuisine": "Mughlai • North Indian • Biryani",
        "rating": 4.2,
        "image_url": "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=600&auto=format&fit=crop&q=80",
        "prep_time": "20-25 min",
        "min_order": 150.0,
        "is_veg_only": 0
    },

    # Vadodara Junction (BRC)
    {
        "station_code": "BRC",
        "name": "Jagdish Foods Rail Express - Vadodara",
        "description": "Heritage Baroda farsan, fresh Khaman Dhokla, Bhakarwadi, Gujarati Thali, and buttermilk.",
        "cuisine": "Gujarati • Snacks • Pure Veg",
        "rating": 4.8,
        "image_url": "https://images.unsplash.com/photo-1601050690597-df0568f70950?w=600&auto=format&fit=crop&q=80",
        "prep_time": "15-20 min",
        "min_order": 90.0,
        "is_veg_only": 1
    },
    {
        "station_code": "BRC",
        "name": "IRCTC Food Plaza - Vadodara",
        "description": "Multi-cuisine food plaza providing quick berth delivery for morning breakfasts and dinner thalis.",
        "cuisine": "North Indian • Chinese • South Indian",
        "rating": 4.3,
        "image_url": "https://images.unsplash.com/photo-1589302168068-964664d93dc0?w=600&auto=format&fit=crop&q=80",
        "prep_time": "20-25 min",
        "min_order": 100.0,
        "is_veg_only": 0
    },

    # Surat (ST)
    {
        "station_code": "ST",
        "name": "Surat Diamond Rail Kitchen",
        "description": "Famous Surati Locho, Sev Khamani, Undhiyu Puri, and deluxe Kathiyawadi vegetarian meals.",
        "cuisine": "Kathiyawadi • Gujarati • Street Food",
        "rating": 4.6,
        "image_url": "https://images.unsplash.com/photo-1546833999-b9f581a1996d?w=600&auto=format&fit=crop&q=80",
        "prep_time": "15-20 min",
        "min_order": 100.0,
        "is_veg_only": 1
    },

    # Mumbai Central (MMCT)
    {
        "station_code": "MMCT",
        "name": "IRCTC Mumbai Central Food Court",
        "description": "Full service station concourse restaurant preparing Pav Bhaji, Biryanis, Coastal curries, and Thalis.",
        "cuisine": "Maharashtrian • North Indian • South Indian",
        "rating": 4.5,
        "image_url": "https://images.unsplash.com/photo-1585937421612-70a008356fbe?w=600&auto=format&fit=crop&q=80",
        "prep_time": "15-20 min",
        "min_order": 120.0,
        "is_veg_only": 0
    },
    {
        "station_code": "MMCT",
        "name": "Tibbs Frankie & Express Snacks",
        "description": "Mumbai's favorite Frankies, grilled sandwiches, iced teas, and cold beverages delivered to coach.",
        "cuisine": "Fast Food • Rolls • Beverages",
        "rating": 4.3,
        "image_url": "https://images.unsplash.com/photo-1626777552726-4a6b54c97e46?w=600&auto=format&fit=crop&q=80",
        "prep_time": "10-15 min",
        "min_order": 80.0,
        "is_veg_only": 0
    },

    # Ajmer Junction (AII)
    {
        "station_code": "AII",
        "name": "Ajmer Sharif Rail Rasoi",
        "description": "Authentic fragrant Dum Biryani, chicken korma, roomali roti, and traditional kheer.",
        "cuisine": "Mughlai • North Indian • Biryani",
        "rating": 4.5,
        "image_url": "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=600&auto=format&fit=crop&q=80",
        "prep_time": "20-25 min",
        "min_order": 120.0,
        "is_veg_only": 0
    },
    {
        "station_code": "AII",
        "name": "Shri Mahaveer Bhojanalaya - Ajmer",
        "description": "Pure ghee Rajasthani thali, Gatta curry, Dal Baati, Missi Roti, and fresh buttermilk.",
        "cuisine": "Pure Veg • Rajasthani Thali",
        "rating": 4.6,
        "image_url": "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=600&auto=format&fit=crop&q=80",
        "prep_time": "15-20 min",
        "min_order": 90.0,
        "is_veg_only": 1
    }
]

# Standard food catalog per category
STANDARD_ITEMS = {
    "Meals": [
        {
            "name": "IRCTC Standard Veg Thali",
            "description": "Steamed basmati rice, dal tadka, seasonal vegetable, 2 chapatis, curd, pickle & gulab jamun.",
            "category": "Meals",
            "price": 180.0,
            "is_veg": 1,
            "rating": 4.5,
            "image_url": "https://images.unsplash.com/photo-1546833999-b9f581a1996d?w=400&auto=format&fit=crop&q=80"
        },
        {
            "name": "Deluxe Rail Maharaja Thali",
            "description": "Jeera rice, paneer butter masala, dal makhani, mix veg, 3 butter rotis, raita, papad, salad & 2 gulab jamuns.",
            "category": "Meals",
            "price": 260.0,
            "is_veg": 1,
            "rating": 4.8,
            "image_url": "https://images.unsplash.com/photo-1585937421612-70a008356fbe?w=400&auto=format&fit=crop&q=80"
        },
        {
            "name": "Jain Special Thali (No Onion No Garlic)",
            "description": "Sattvic yellow dal, paneer in tomato gravy, aloo methi, steamed rice, 3 phulkas, curd & sweet.",
            "category": "Meals",
            "price": 210.0,
            "is_veg": 1,
            "rating": 4.6,
            "image_url": "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=400&auto=format&fit=crop&q=80"
        },
        {
            "name": "Hyderabadi Chicken Dum Biryani",
            "description": "Slow cooked fragrant long-grain biryani with tender chicken pieces, served with spicy mirchi ka salan & raita.",
            "category": "Meals",
            "price": 240.0,
            "is_veg": 0,
            "rating": 4.7,
            "image_url": "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=400&auto=format&fit=crop&q=80"
        }
    ],
    "Breakfast": [
        {
            "name": "South Indian Masala Dosa Combo",
            "description": "Crispy golden butter dosa with spiced potato stuffing, served with hot vegetable sambar and fresh coconut chutney.",
            "category": "Breakfast",
            "price": 120.0,
            "is_veg": 1,
            "rating": 4.6,
            "image_url": "https://images.unsplash.com/photo-1610192244261-3f33de3f55e4?w=400&auto=format&fit=crop&q=80"
        },
        {
            "name": "Idli Sambar & Medu Vada (2+1)",
            "description": "2 steamed soft idlis and 1 crispy medu vada with hot lentil sambar and two styles of chutneys.",
            "category": "Breakfast",
            "price": 100.0,
            "is_veg": 1,
            "rating": 4.4,
            "image_url": "https://images.unsplash.com/photo-1589301760014-d929f3979dbc?w=400&auto=format&fit=crop&q=80"
        },
        {
            "name": "Bedmi Puri with Aloo Sabzi (4 pcs)",
            "description": "Crispy urad dal stuffed puris served with spicy Delhi-style potato gravy, pickle, and green chili.",
            "category": "Breakfast",
            "price": 110.0,
            "is_veg": 1,
            "rating": 4.5,
            "image_url": "https://images.unsplash.com/photo-1601050690597-df0568f70950?w=400&auto=format&fit=crop&q=80"
        },
        {
            "name": "Indori Poha with Ratlami Sev & Jalebi",
            "description": "Steamed light flattened rice with jeeravan spices, topped with crunchy Ratlami sev and 2 hot jalebis.",
            "category": "Breakfast",
            "price": 90.0,
            "is_veg": 1,
            "rating": 4.7,
            "image_url": "https://images.unsplash.com/photo-1565299585323-38d6b0865b47?w=400&auto=format&fit=crop&q=80"
        }
    ],
    "North Indian": [
        {
            "name": "Paneer Butter Masala with 3 Garlic Naan",
            "description": "Cottage cheese cubes simmered in rich creamy tomato and cashew nut gravy, paired with 3 butter tandoori naans.",
            "category": "North Indian",
            "price": 220.0,
            "is_veg": 1,
            "rating": 4.7,
            "image_url": "https://images.unsplash.com/photo-1589302168068-964664d93dc0?w=400&auto=format&fit=crop&q=80"
        },
        {
            "name": "Dal Makhani & Jeera Rice Bowl",
            "description": "Overnight slow-cooked black lentils in butter and cream served over fragrant cumin spiced rice.",
            "category": "North Indian",
            "price": 160.0,
            "is_veg": 1,
            "rating": 4.6,
            "image_url": "https://images.unsplash.com/photo-1546833999-b9f581a1996d?w=400&auto=format&fit=crop&q=80"
        },
        {
            "name": "Butter Chicken with 3 Laccha Parathas",
            "description": "Boneless tandoori chicken cooked in velvety tomato cream sauce with 3 layered crisp whole wheat parathas.",
            "category": "North Indian",
            "price": 270.0,
            "is_veg": 0,
            "rating": 4.8,
            "image_url": "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=400&auto=format&fit=crop&q=80"
        },
        {
            "name": "Chole Bhature (2 pcs)",
            "description": "Authentic Punjabi spicy chickpea curry with 2 fluffy bhaturas, pickled onions, and mint chutney.",
            "category": "North Indian",
            "price": 150.0,
            "is_veg": 1,
            "rating": 4.7,
            "image_url": "https://images.unsplash.com/photo-1626777552726-4a6b54c97e46?w=400&auto=format&fit=crop&q=80"
        }
    ],
    "South Indian": [
        {
            "name": "Ghee Roast Masala Dosa",
            "description": "Crispy golden crepe roasted in pure desi ghee, layered with potato masala and podi powder.",
            "category": "South Indian",
            "price": 140.0,
            "is_veg": 1,
            "rating": 4.7,
            "image_url": "https://images.unsplash.com/photo-1610192244261-3f33de3f55e4?w=400&auto=format&fit=crop&q=80"
        },
        {
            "name": "Onion Tomato Uttapam (2 pcs)",
            "description": "Thick spongy fermented rice pancakes topped with finely chopped onions, tomatoes, green chilies, and curry leaves.",
            "category": "South Indian",
            "price": 130.0,
            "is_veg": 1,
            "rating": 4.5,
            "image_url": "https://images.unsplash.com/photo-1589301760014-d929f3979dbc?w=400&auto=format&fit=crop&q=80"
        },
        {
            "name": "Curd Rice with South Indian Tadka",
            "description": "Cooling spiced yogurt rice tempered with mustard seeds, curry leaves, ginger, and pomegranate pearls.",
            "category": "South Indian",
            "price": 110.0,
            "is_veg": 1,
            "rating": 4.4,
            "image_url": "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=400&auto=format&fit=crop&q=80"
        }
    ],
    "Snacks": [
        {
            "name": "Special Punjabi Samosas (2 pcs)",
            "description": "Crisp flaky pastry pockets loaded with spiced potatoes, green peas, and cashews with tamarind chutney.",
            "category": "Snacks",
            "price": 50.0,
            "is_veg": 1,
            "rating": 4.5,
            "image_url": "https://images.unsplash.com/photo-1601050690597-df0568f70950?w=400&auto=format&fit=crop&q=80"
        },
        {
            "name": "Mumbai Pav Bhaji (2 Butter Pav)",
            "description": "Mashed spiced vegetable curry cooked on a tawa with dollops of Amul butter, served with 2 warm butter pavs.",
            "category": "Snacks",
            "price": 130.0,
            "is_veg": 1,
            "rating": 4.6,
            "image_url": "https://images.unsplash.com/photo-1626777552726-4a6b54c97e46?w=400&auto=format&fit=crop&q=80"
        },
        {
            "name": "Authentic Ratlami Sev Pouch (250g)",
            "description": "Crispy clove-spiced gram flour snack noodles directly from Ratlam junction.",
            "category": "Snacks",
            "price": 75.0,
            "is_veg": 1,
            "rating": 4.9,
            "image_url": "https://images.unsplash.com/photo-1565299585323-38d6b0865b47?w=400&auto=format&fit=crop&q=80"
        },
        {
            "name": "Grilled Paneer Tikka Sandwich",
            "description": "Jumbo toasted triple-layer bread stuffed with spiced tandoori paneer, crunchy veggies, and mint mayo.",
            "category": "Snacks",
            "price": 120.0,
            "is_veg": 1,
            "rating": 4.4,
            "image_url": "https://images.unsplash.com/photo-1528735602780-2552fd46c7af?w=400&auto=format&fit=crop&q=80"
        }
    ],
    "Beverages": [
        {
            "name": "Railway Kulhad Masala Chai (2 Cups)",
            "description": "Ginger and cardamom infused hot tea brewed with full cream milk, served in traditional earthen kulhads.",
            "category": "Beverages",
            "price": 40.0,
            "is_veg": 1,
            "rating": 4.8,
            "image_url": "https://images.unsplash.com/photo-1576092768241-dec231879fc3?w=400&auto=format&fit=crop&q=80"
        },
        {
            "name": "South Indian Filter Coffee (2 Cups)",
            "description": "Strong decoction filter coffee frothed to perfection with fresh boiled milk.",
            "category": "Beverages",
            "price": 60.0,
            "is_veg": 1,
            "rating": 4.7,
            "image_url": "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?w=400&auto=format&fit=crop&q=80"
        },
        {
            "name": "Punjabi Malai Sweet Lassi (350ml)",
            "description": "Thick churned sweet yogurt drink topped with a layer of fresh clotted cream and pistachios.",
            "category": "Beverages",
            "price": 70.0,
            "is_veg": 1,
            "rating": 4.6,
            "image_url": "https://images.unsplash.com/photo-1553787499-6f9133860278?w=400&auto=format&fit=crop&q=80"
        },
        {
            "name": "Rail Neer Packaged Drinking Water (1L)",
            "description": "IRCTC certified purified mineral water bottle with sealed cap.",
            "category": "Beverages",
            "price": 15.0,
            "is_veg": 1,
            "rating": 5.0,
            "image_url": "https://images.unsplash.com/photo-1548839140-29a749e1bc4e?w=400&auto=format&fit=crop&q=80"
        }
    ],
    "Desserts": [
        {
            "name": "Hot Gulab Jamun (2 pcs)",
            "description": "Golden brown fried khoya dumplings soaked in fragrant saffron and cardamom sugar syrup.",
            "category": "Desserts",
            "price": 60.0,
            "is_veg": 1,
            "rating": 4.7,
            "image_url": "https://images.unsplash.com/photo-1589302168068-964664d93dc0?w=400&auto=format&fit=crop&q=80"
        },
        {
            "name": "Kolkata Spongy Rasgulla (2 pcs)",
            "description": "Soft and spongy cottage cheese balls steeped in clear light sugar syrup.",
            "category": "Desserts",
            "price": 60.0,
            "is_veg": 1,
            "rating": 4.6,
            "image_url": "https://images.unsplash.com/photo-1546833999-b9f581a1996d?w=400&auto=format&fit=crop&q=80"
        },
        {
            "name": "Rajasthani Malai Rabri Ghevar",
            "description": "Traditional honeycomb disc sweet soaked in syrup and coated with rich cardamom rabri and almond flakes.",
            "category": "Desserts",
            "price": 95.0,
            "is_veg": 1,
            "rating": 4.8,
            "image_url": "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=400&auto=format&fit=crop&q=80"
        }
    ]
}

OFFICIAL_PARTNERS = [
    {
        "slug": "irctc-ecatering",
        "name": "IRCTC eCatering",
        "tagline": "Official Railway Catering",
        "description": "Official food delivery platform of Indian Railways delivering hot, hygienic meals at berths across 450+ stations.",
        "logo_icon": "fa-train-subway",
        "website_url": "https://www.ecatering.irctc.co.in/",
        "cuisines": "IRCTC eCatering, Indian, South Indian, Fast Food, Vegetarian",
        "is_featured": 1,
        "is_official": 1
    },
    {
        "slug": "dominos",
        "name": "Domino's Pizza",
        "tagline": "Hot Pizza on Train",
        "description": "Pizzas, garlic bread, stuffed garlic breads, and choco lava cakes delivered piping hot to your coach seat.",
        "logo_icon": "fa-pizza-slice",
        "website_url": "https://www.ecatering.irctc.co.in/",
        "cuisines": "Pizza, Fast Food, Desserts, Beverages, Vegetarian, Non-Vegetarian",
        "is_featured": 1,
        "is_official": 1
    },
    {
        "slug": "zomato",
        "name": "Zomato",
        "tagline": "Multi-Restaurant Train Delivery",
        "description": "Partnered with IRCTC to deliver freshly cooked orders from top local city restaurants directly at major railway stations.",
        "logo_icon": "fa-utensils",
        "website_url": "https://www.zomato.com/",
        "cuisines": "Indian, Biryani, Pizza, Fast Food, South Indian, Desserts, Vegetarian, Non-Vegetarian",
        "is_featured": 1,
        "is_official": 1
    },
    {
        "slug": "swiggy",
        "name": "Swiggy",
        "tagline": "Station Berth Delivery",
        "description": "Delivering curated food selections from verified restaurant brands across selected railway junctions nationwide.",
        "logo_icon": "fa-burger",
        "website_url": "https://www.swiggy.com/",
        "cuisines": "Indian, Biryani, Fast Food, Desserts, Beverages, Vegetarian, Non-Vegetarian",
        "is_featured": 1,
        "is_official": 1
    },
    {
        "slug": "zoop",
        "name": "Zoop",
        "tagline": "IRCTC Approved Food Aggregator",
        "description": "Dedicated train meal delivery service authorized by IRCTC for WhatsApp and online train berth delivery.",
        "logo_icon": "fa-bowl-food",
        "website_url": "https://www.zoopindia.com/",
        "cuisines": "IRCTC eCatering, Indian, Biryani, South Indian, Vegetarian",
        "is_featured": 0,
        "is_official": 1
    },
    {
        "slug": "railyatri",
        "name": "RailYatri",
        "tagline": "Meals on Train",
        "description": "Hygienic thalis, combo meals, and snacks delivered to train seats with live tracking updates.",
        "logo_icon": "fa-box-tissue",
        "website_url": "https://www.railyatri.in/meals-on-train",
        "cuisines": "IRCTC eCatering, Indian, South Indian, Beverages, Vegetarian",
        "is_featured": 0,
        "is_official": 1
    },
    {
        "slug": "ovenstory",
        "name": "Ovenstory Pizza",
        "tagline": "Signature Standout Pizzas",
        "description": "Cheesy handcrafted pizzas with distinct cheese bases delivered at scheduled junction halts.",
        "logo_icon": "fa-pizza-slice",
        "website_url": "https://www.ecatering.irctc.co.in/",
        "cuisines": "Pizza, Fast Food, Beverages, Vegetarian, Non-Vegetarian",
        "is_featured": 0,
        "is_official": 1
    },
    {
        "slug": "faasos",
        "name": "Faasos",
        "tagline": "Signature Wraps & Rolls",
        "description": "Hearty rolls, wraps, rice bowls, and quick railway bites freshly wrapped and delivered.",
        "logo_icon": "fa-bread-slice",
        "website_url": "https://www.ecatering.irctc.co.in/",
        "cuisines": "Fast Food, Indian, Beverages, Vegetarian, Non-Vegetarian",
        "is_featured": 0,
        "is_official": 1
    },
    {
        "slug": "lunchbox",
        "name": "Lunchbox",
        "tagline": "Homestyle Meals & Thalis",
        "description": "Wholesome homestyle thalis, paratha meals, and rajma chawal prepared with traditional recipes.",
        "logo_icon": "fa-bowl-rice",
        "website_url": "https://www.ecatering.irctc.co.in/",
        "cuisines": "Indian, Vegetarian",
        "is_featured": 0,
        "is_official": 1
    },
    {
        "slug": "behrouz-biryani",
        "name": "Behrouz Biryani",
        "tagline": "Royal Dum Biryani",
        "description": "Slow-cooked royal biryanis packed in sealed insulated handis with gulab jamun and raita.",
        "logo_icon": "fa-fire-burner",
        "website_url": "https://www.ecatering.irctc.co.in/",
        "cuisines": "Biryani, Indian, Non-Vegetarian",
        "is_featured": 0,
        "is_official": 1
    },
    {
        "slug": "haldirams",
        "name": "Haldiram's",
        "tagline": "Pure Veg Sweets & Savouries",
        "description": "Pure vegetarian North Indian meals, traditional chaat, samosas, packaged namkeens, and festive sweets.",
        "logo_icon": "fa-leaf",
        "website_url": "https://www.haldirams.com/",
        "cuisines": "Vegetarian, Indian, Desserts, Fast Food, Beverages",
        "is_featured": 0,
        "is_official": 1
    },
    {
        "slug": "comesum",
        "name": "Comesum",
        "tagline": "24x7 Rail Concourse Food Plaza",
        "description": "24x7 multi-cuisine railway restaurant serving express travelers at railway platforms across India.",
        "logo_icon": "fa-store",
        "website_url": "https://comesum.com/",
        "cuisines": "Indian, South Indian, Fast Food, Beverages, Vegetarian, Non-Vegetarian",
        "is_featured": 0,
        "is_official": 1
    }
]

