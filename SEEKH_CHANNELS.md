# Alag-alag channel ki seekh (24 Nov 2026)
Katha Chitra (Ramayan, alag repo katha-chitra-videos) mein insaani body language seekhi gayi. Yahan har channel par wahi lagta hai jo uske topic mein kaam ka hai:
- **Katha / Bhakti Shorts (katha.py):** AI tasveer mein insaan ke haath (paanch ungli), natural pose, chehre ka bhaav, har character ka alag body language prompt mein zaroori. Camera chaal ab slow-in/slow-out (jhatka nahi).
- **Free Fire (main.py) aur Car (car_game.py):** insaani character nahi, isliye body wala hissa nahi. Sirf bolchaal ka niyam: aaj ki aasaan bolchaal ki Hindi, chhote natural vaakya, bhaari kitabi shabd nahi.
- Ramayan wale poore niyam (Valmiki, character bible) yahan nahi lagte; wo sirf Katha Chitra ke hain.

## Nayi baat (27 Nov 2026): AWS backup (Free Fire, Car, Katha)
- free_ai.py mein: Gemini fail ho to pehle AWS (Opus 4.6), phir GitHub Models. Har channel ki apni ginti, 30 call roz. AWS 20 May 2027 ke baad band.
- Chalne ke liye is repo mein secret AWS_BEARER_TOKEN_BEDROCK aur variable AWS_AI = on dono chahiye. Asli test PASS (27 Nov raat 1:27, "AWS test (bina upload)" workflow, Opus 4.6 ne jawab diya). Asli video run mein AWS abhi nahi dekha gaya.
- AWS Free plan hi rahe; Upgrade kabhi nahi. Key code, log ya chat mein kabhi nahi.
- 26 Nov ki failure: Car mein Gemini busy tha aur GitHub Models backup bhi nahi chala. Katha mein Cloudflare ki roz ki free seema (tasveer) khatam thi; AWS wala text backup is tasveer wali dikkat ko theek NAHI karta.

## 27 Nov raat: tasveer backup aur retry
- AWS key se tasveer wale model nahi mile: ap-southeast-2 ki list khali; us-east-1 aur us-west-2 account ki policy se band. AWS abhi sirf likhne ka backup hai.
- Gemini ki tasveer: free seema 429. Pollinations (bina chaabi): chala, par tasveer katha se bilkul alag aur watermark wali, isliye NAHI lagaya (img-test branch). Galat bhagwan tasveer public nahi jani chahiye.
- ai_helper.py: fail run ka rerun sirf tab jab upload shuru hi na hua ho (double video se bachav). AWS env bhi ab AI Helper mein hai.
