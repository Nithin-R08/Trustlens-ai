export const projects = [
  {
    title: "TrustLens AI \u2013 Dataset Bias Detection Platform",
    tech: ["React", "Node.js", "Python", "LLM"],
    description: [
      "Engineered an AI-powered bias detection system computing 8+ fairness metrics (demographic parity, equalized odds) with LLM-generated explainable audit reports.",
      "Top 5 Finalist at CUK-CS Hackathon (80+ teams); reduced manual bias review time by 60% for non-technical users."
    ],
    github: "#"
  },
  {
    title: "Smart Crop Disease Detector",
    tech: ["Python", "CNN", "OpenCV"],
    description: [
      "Built a CNN model achieving 92% classification accuracy across 15 disease categories with OpenCV preprocessing cutting inference latency by 40%.",
      "Designed an early-warning decision-support interface to assist 200+ farmers with real-time crop disease alerts."
    ],
    github: "https://github.com/Nithin-R08/Smart-Crop-Disease-Detector"
  },
  {
    title: "Crypto Wallet for Newbies",
    tech: ["React", "Node.js", "MongoDB", "Web3"],
    description: [
      "Built a secure Ethereum wallet with JWT authentication, AES-encrypted wallet creation, and real-time blockchain transactions supporting 5+ ERC-20 tokens.",
      "Streamlined UX to reduce onboarding steps by 50%, making Web3 accessible to non-technical users."
    ],
    github: "https://github.com/Nithin-R08/Crypto-Wallet-for-Newbies"
  },
  {
    title: "Travel Management System",
    tech: ["Next.js", "Google Maps API", "Firebase"],
    description: [
      "Deployed a responsive travel app with real-time location search and turn-by-turn navigation via Google Maps API, serving 100+ test users.",
      "Implemented Firebase Auth and Firestore for secure, real-time cross-device data synchronization."
    ],
    github: "https://github.com/Nithin-R08/TravelEase_Travel-Maanagement-System"
  }
] as const;
