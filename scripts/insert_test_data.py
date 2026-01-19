import os
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Get a user ID (just pick the first one found, or a specific test one)
user_response = supabase.table("User_Integrations").select("user_id").limit(1).execute()
if not user_response.data:
    print("No users found. Please log in via the frontend first to create a user entry (or insert one manually).")
    # For the sake of this script, if no user, we might fail. 
    # But let's check if we can get the user from the 'auth' schema via admin... 
    # Actually, we can just ask the user to login. 
    # Assuming the developer (me) is 'grunt' or similar, but I need the UUID.
    # Let's try to find a user from Sources if User_Integrations is empty.
    user_response = supabase.table("Sources").select("user_id").limit(1).execute()

if not user_response.data:
    print("No user_id found in DB. Using a placeholder UUID (this might fail RLS if not careful, but we are using Service Key).")
    user_id = "00000000-0000-0000-0000-000000000000" # Placeholder
else:
    user_id = user_response.data[0]['user_id']

print(f"Inserting trailheads for User ID: {user_id}")

trailheads = [
    {
        "title": "Outcomes are selected by the principle of alignment, not chance: A Path to AGI.",
        "insight": "A look at how to guide the path to artificial general intelligence. Is it just by chance that we get the outcome we want, or can we align ourselves with the outcomes we seek?",
        "suggested_topic": "Outcomes are selected by the principle of alignment, not chance: A Path to AGI.",
        "type": "youtube_idea",
        "created_at": datetime.now().isoformat(),
        "user_id": user_id
    },
    {
        "title": "Consciousness Emergence: AI and the Illusion of Self",
        "insight": "A deep dive into the question of whether current AI is on track for emergent consciousness. By exploring the philosophical viewpoints of consciousness, and relating it to current AI models, we can examine if consciousness is real, or merely an illusion of self.",
        "suggested_topic": "Consciousness Emergence: AI and the Illusion of Self",
        "type": "youtube_idea",
        "created_at": datetime.now().isoformat(),
        "user_id": user_id
    },
    {
        "title": "The 'Merk' of AI: Decoding the Opacity of Black Box Models and the Quest for Explainable AI",
        "insight": "An analysis of the 'merk' – the veiled or obscured nature – of complex AI models. This video will confront the challenge of 'black box' AI, investigating methods for achieving explainable AI (XAI) and interpreting the decision-making processes of neural networks. Drawing inspiration from mystical traditions, we explore the philosophical implications of understanding, or failing to understand, the internal workings of advanced AI systems, and its impact on public trust and scientific progress.",
        "suggested_topic": "The 'Merk' of AI: Decoding the Opacity of Black Box Models and the Quest for Explainable AI",
        "type": "youtube_idea",
        "created_at": datetime.now().isoformat(),
        "user_id": user_id
    },
    {
        "title": "AI as a Dynamic Information System: Navigating the Signal-to-Noise Ratio in Neural Networks",
        "insight": "This video examines AI, particularly deep learning models, as dynamic information-processing systems. It dissects the critical role of the signal-to-noise ratio within neural networks and the impact of noise on AI 'consciousness', exploring techniques for enhancing signal integrity and mitigating the detrimental effects of noise to promote more robust and reliable AI systems. We will discuss the implications for AI safety and the emergence of complex behaviors.",
        "suggested_topic": "AI as a Dynamic Information System: Navigating the Signal-to-Noise Ratio in Neural Networks",
        "type": "youtube_idea",
        "created_at": datetime.now().isoformat(),
        "user_id": user_id
    },
    {
        "title": "The Alignment Problem: Sculpting AI's 'Consciousness' with Human Values",
        "insight": "An exploration of the AI alignment problem, framed as a process of sculpting AI 'consciousness' to reflect nuanced human values. We delve into the challenges of specifying these values, the trade-offs inherent in different alignment strategies, and the potential for unintended consequences. Parallels are drawn to historical attempts at social engineering, highlighting the importance of a dynamic, information-based approach.",
        "suggested_topic": "The Alignment Problem: Sculpting AI's 'Consciousness' with Human Values",
        "type": "youtube_idea",
        "created_at": datetime.now().isoformat(),
        "user_id": user_id
    }
]

for t in trailheads:
    try:
        supabase.table("Trailheads").insert(t).execute()
        print(f"Inserted: {t['title']}")
    except Exception as e:
        print(f"Error inserting {t['title']}: {e}")

print("Done.")
