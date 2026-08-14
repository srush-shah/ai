"""
Labeled test cases for category classification evaluation.
Each case: (description, expected_leaf_category_id, notes)
"""

TEST_CASES = [
    # ── FOOD & ESSENTIALS ────────────────────────────────────────────────────
    ("I need help finding a local food bank because I'm short on groceries this week.", "1.1", "food bank"),
    ("Can someone help me pick up groceries and deliver them to my door?", "1.2", "grocery delivery"),
    ("I need help cooking a basic meal, I don't know how to cook.", "1.3.1", "basic meal prep"),
    ("I'm preparing food for a Diwali celebration and need cooking help.", "1.3.2", "festive cooking"),
    ("I want to learn how to plan balanced nutritious meals.", "1.3.3", "nutrition planning"),
    ("I need help learning to cook traditional Indian food.", "1.3.4", "cultural cuisine"),
    ("I need assistance getting government food assistance / SNAP benefits.", "1.1", "food assistance program"),

    # ── CLOTHING ─────────────────────────────────────────────────────────────
    ("I have a bag of old clothes I want to donate.", "2.1", "donate clothes"),
    ("I need some clothes for my kids — we can't afford to buy them right now.", "2.2", "borrow clothes"),
    ("My house burned down and I need emergency clothing immediately.", "2.3", "emergency clothing"),
    ("I need a tailor to fix the zipper on my pants.", "2.4", "tailoring"),

    # ── HOUSING — REPAIR ─────────────────────────────────────────────────────
    ("My kitchen sink is leaking and I need a plumber.", "3.3.1", "plumbing"),
    ("I need someone to fix a few things around the house — hang a shelf, patch a hole.", "3.3.2", "handyman"),
    ("The lights in my apartment stopped working, I need an electrician.", "3.3.3", "electrician"),
    ("My wooden cabinet door broke off, I need carpentry help.", "3.3.4", "carpentry"),
    ("My backyard is overgrown and I need someone to mow and trim it.", "3.3.5", "garden"),
    ("My air conditioner stopped cooling and it's very hot.", "3.3.6", "hvac"),
    ("There's a leak in my roof after the rain.", "3.3.7", "roofing"),
    ("I'm locked out of my house and need a locksmith.", "3.3.8", "locksmith"),
    ("I want to repaint my living room walls.", "3.3.9", "painting"),

    # ── HOUSING — OTHER ──────────────────────────────────────────────────────
    ("I don't understand my lease agreement and need help reading it.", "3.1", "lease"),
    ("My landlord is trying to evict me and I need help with tenant rights.", "3.2", "tenant rights"),
    ("I just moved in and need help setting up internet and electricity.", "3.4", "utilities setup"),
    ("I'm looking for a 2-bedroom apartment to rent.", "3.5", "looking for rental"),
    ("I'm looking for a roommate to share my apartment.", "3.6", "find roommate"),
    ("I need help packing and moving my furniture to a new place.", "3.7", "move in help"),
    ("I need help booking a moving company for next weekend.", "3.8", "packers movers"),
    ("I need to buy a used couch and dining table.", "3.9", "buy things"),
    ("I want to sell my old TV and microwave.", "3.10", "sell things"),

    # ── EDUCATION & CAREER ───────────────────────────────────────────────────
    ("I need help writing my college application essays.", "4.1", "college application"),
    ("Can someone review my statement of purpose for grad school?", "4.2", "SOP review"),
    ("I need a math tutor for my 10th grade exams.", "4.3.1", "math tutoring"),
    ("I need help with English grammar and writing.", "4.3.2", "english tutoring"),
    ("I need a science tutor for chemistry.", "4.3.3", "science tutoring"),
    ("I need help learning Python and data structures.", "4.3.4", "CS tutoring"),
    ("I'm preparing for the GRE and need study help.", "4.3.5", "test prep"),
    ("I need information about scholarships for international students.", "4.4", "scholarships"),
    ("I want to form a study group for my upcoming exams.", "4.5", "study group"),
    ("I need resume review and help preparing for job interviews.", "4.6", "career guidance"),
    ("Where can I find free online courses and textbooks?", "4.7", "education resources"),

    # ── HEALTHCARE ───────────────────────────────────────────────────────────
    ("I have a fever, body aches, and sore throat. I need to see a doctor.", "5.1.1", "general consultation"),
    ("I have an ear infection and sinus pain, I need an ENT doctor.", "5.1.2", "ENT"),
    ("I have a toothache and need a dentist.", "5.1.3", "dental"),
    ("My vision is blurry and I need an eye exam.", "5.1.4", "eye care"),
    ("I have high blood pressure and chest pain, need a cardiologist.", "5.1.5", "cardiac"),
    ("My knee hurts after a fall and I need a physiotherapist.", "5.1.6", "orthopedic"),
    ("I have a skin rash and need a dermatologist.", "5.1.7", "dermatology"),
    ("I need help finding a gynecologist for a routine checkup.", "5.1.8", "womens health"),
    ("My child needs vaccinations before starting school.", "5.1.9", "vaccinations"),
    ("My toddler has a fever and rash, I need a pediatrician.", "5.1.10", "pediatrics"),
    ("I need someone to pick up my prescription medication from the pharmacy.", "5.2", "medicine delivery"),
    ("I'm feeling very anxious and depressed and need someone to talk to.", "5.3", "mental health"),
    ("I need reminders to take my blood pressure pills every morning.", "5.4", "medication reminders - no elderly trigger"),
    ("What are good sleep habits for better health?", "5.5", "health education"),

    # ── ELDERLY — CLEAR CASES ────────────────────────────────────────────────
    ("My 80-year-old grandmother needs help using her smartphone and apps.", "6.2", "elderly digital support"),
    ("My grandfather needs help managing his multiple medications.", "6.3", "elderly medication management"),
    ("My elderly father needs someone to drive him to his doctor appointments.", "6.6", "elderly transport"),
    ("My grandmother is lonely and would like a volunteer to visit and chat with her.", "6.8", "elderly social connection"),
    ("The senior living facility needs help organizing meal preparation for residents.", "6.9", "elderly meal support"),
    ("My aging parent needs help setting up a medical alert device at home.", "6.4", "medical devices setup"),
    ("I need help scheduling medical appointments for my elderly mother.", "6.7", "scheduling for elderly"),
    ("Senior citizen needs help running errands like grocery pickup.", "6.5", "elderly errands"),
    ("My retired grandfather is moving to an assisted living facility and needs help.", "6.1", "senior relocation"),

    # ── ELDERLY vs HEALTHCARE BOUNDARY ───────────────────────────────────────
    # These should go to HEALTHCARE, NOT elderly
    ("I need medication reminders for myself — I keep forgetting my morning pills.", "5.4", "medication reminders, no elderly context"),
    ("I need help finding a doctor for a general checkup for myself.", "5.1.1", "general checkup, no elderly"),
    ("I want to understand how to take care of my health better.", "5.5", "health education, no elderly"),
    ("My mom has a doctor appointment next week, can someone drive her?", "6.6", "weak trigger + cue -> elderly transport"),
    ("My father needs help with medication reminders.", "6.3", "weak trigger + medication -> elderly"),

    # ── ELDERLY vs FOOD BOUNDARY ─────────────────────────────────────────────
    ("I'm a senior and I need help getting meals delivered to me.", "6.9", "elderly meal support"),
    ("I need help finding a food bank in my area.", "1.1", "food bank, no elderly context"),

    # ── ELDERLY-KEYWORD FALSE POSITIVES ──────────────────────────────────────
    # An elderly person is mentioned, but the actual help needed is a normal
    # task in another branch. is_elderly_context() fires on the keyword, so these
    # separate "boost" (robust) from "route" (forces a wrong elderly leaf).
    ("My elderly mother wants help finding a math tutor for my son.", "4.3.1", "elderly keyword, real task = math tutoring"),
    ("My grandfather needs a plumber to fix his leaking kitchen sink.", "3.3.1", "elderly keyword, real task = plumbing"),
    ("My retired father wants help selling his old furniture.", "3.10", "elderly keyword, real task = sell things"),
    ("My senior neighbor has a bag of old clothes she wants to donate.", "2.1", "elderly keyword, real task = donate clothes"),
    ("My grandmother needs an electrician — the lights in her house stopped working.", "3.3.3", "elderly keyword, real task = electrician"),

    # ── GENERAL / UNCLEAR ────────────────────────────────────────────────────
    ("I'm not sure what kind of help I need.", "0.0.0.0.0", "unclear"),
    ("Can you help me with something general?", "0.0.0.0.0", "vague request"),
]
