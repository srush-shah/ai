# Fresh holdout test cases — written independently of the original 77-case set.
# Covers a broad range of categories with natural phrasings, boundary cases,
# and false positives. Do NOT use these to tune routing or descriptions.

FRESH_TEST_CASES = [
    # --- Food & Essentials ---
    ("I haven't eaten in two days and need help finding a food bank nearby.", "1.1", "food bank access"),
    ("Could a volunteer help me shop for and deliver groceries to my apartment?", "1.2", "grocery delivery"),
    ("We are hosting a Navratri dinner for forty guests and need cooking help.", "1.3.2", "festive bulk cooking"),
    ("I want to recreate my grandmother's biryani but need step-by-step guidance on the recipe.", "1.3.4", "cultural cuisine"),
    ("I would like to learn how to plan nutritious weekly meals on a tight budget.", "1.3.3", "nutrition planning"),

    # --- Clothing ---
    ("I have bags of old coats and sweaters I would like to donate to someone in need.", "2.1", "clothes donation"),
    ("The hem on my dress trousers is coming undone before an important interview.", "2.4", "tailoring"),

    # --- Housing: repairs ---
    ("My kitchen sink has been clogged for two days and water refuses to drain.", "3.3.1", "plumbing"),
    ("My bedroom ceiling fan stopped spinning — I suspect a wiring problem.", "3.3.3", "electrician"),
    ("My home heater broke down and temperatures are dropping overnight.", "3.3.6", "HVAC"),
    ("I locked myself out of my apartment and need a locksmith urgently.", "3.3.8", "locksmith"),

    # --- Housing: other ---
    ("My landlord sent an eviction notice even though I paid my rent on time.", "3.2", "tenant rights"),
    ("I need help packing and loading boxes before my move next weekend.", "3.7", "move-in help"),
    ("I am looking for someone to share a two-bedroom apartment with me.", "3.6", "roommate"),
    ("My parents are downsizing and need professional movers for a long-distance move.", "3.8", "booking movers"),

    # --- Education ---
    ("I cannot wrap my head around calculus derivatives and really need a tutor.", "4.3.1", "math tutoring"),
    ("Could someone review the personal statement I wrote for a master's application?", "4.2", "essay review"),
    ("Where can I find free lecture notes and textbooks for my university courses?", "4.7", "education resources"),
    ("I have a software engineering interview next week and want mock practice.", "4.6", "career guidance"),
    ("My daughter is stuck on a chemistry assignment about chemical reactions.", "4.3.3", "science tutoring"),

    # --- Healthcare ---
    ("I have had a fever, chills, and body aches for two days and feel terrible.", "5.1.1", "general illness"),
    ("I have a severe toothache and think I might need a root canal.", "5.1.3", "dental"),
    ("Can someone pick up my blood pressure prescription from the pharmacy for me?", "5.2", "medicine pickup"),
    ("I have had sharp lower back pain for a week and need to see a specialist.", "5.1.6", "orthopedic"),
    ("I keep forgetting to take my thyroid pill every morning and need reminders.", "5.4", "medication reminders no elderly"),
    ("I have been feeling very down lately and just need someone to talk to.", "5.3", "mental wellbeing"),
    ("My two-year-old has a high fever and a rash — I need a children's doctor.", "5.1.10", "pediatrics"),
    ("My son needs his school vaccination records updated before the new semester starts.", "5.1.9", "vaccinations"),

    # --- Elderly ---
    ("My 82-year-old grandmother cannot figure out how to video call on her tablet.", "6.2", "elderly digital support"),
    ("My elderly uncle needs a volunteer to drive him to his heart specialist appointment.", "6.6", "elderly transport"),
    ("An elderly woman in my building is completely isolated and would love a regular visitor.", "6.8", "elderly social connection"),
    ("My aging father can barely manage daily errands on his own and needs regular help.", "6.5", "elderly errands"),
    ("I am 78 years old and can no longer cook — I need meals brought to my home.", "6.9", "elderly meal support - age number only"),
    ("My grandfather takes seven different medications and keeps mixing up which to take.", "6.3", "elderly medication mgmt"),

    # --- False positives and edge cases ---
    ("I am a senior student at university applying for data science internship positions.", "4.6", "senior student FP - career not elderly"),
    ("I honestly do not know what kind of help I am looking for right now.", "0.0.0.0.0", "genuinely unclear request"),
]
