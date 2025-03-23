# Iris Conversational Voice AI

**A voice-to-voice AI** built with **Django**, **Deepgram**, **OpenAI** and integrated with **Twilio**. Iris is designed to deliver a fun and engaging conversational experience with smart time wasting.

### **Check out the project live**: [irisvoiceai.tech](https://irisvoiceai.tech)
### **Talk to Iris**: Call +1 956-952-7270

#### Update
New features are being developed — including enhanced speech detection & response generation along with UI improvements.

## Features

- **Real-Time Voice Interaction**:  
  Django channels and asynchronous websockets for real-time voice exchange.
  
- **Speech-to-Text (STT) and Text-to-Speech (TTS)**:  
  Deepgram Nova-3 is used to transcribe user speech accurately in real time and Deepgram Aura model for converting text responses to speech.
  
- **Response Generation**:  
  OpenAI GPT-4o Mini tuned to process transcribed text to generate conversational responses.
  
- **Twilio Integration**:  
  Enabling inbound phone calls, allowing users to interact with Iris via phone. 
  
- **Session-based Memory**:  
  Redis is used to simulate conversation memory by storing the conversation history mapped to a user session, providing context for response generation.
  
- **Responsive and Fast**:  
  Optimized asynchronous processing for low latency and a responsive experience for users.

## Deployment

- The application is containerized with **Docker** and pushed to **AWS Elastic Container Registry**.
- Hosted on **AWS EC2** with **Nginx** acting as a reverse proxy, ensuring secure access over **HTTPS**.
- **Redis** is used for session and cache management, with AWS ElastiCache in production.

