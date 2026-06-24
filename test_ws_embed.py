import asyncio
import json
import sys
import websockets

async def chat_loop(ws_url: str):
    print(f"\n🔌 Connecting to GraphMind WebSocket API...")
    print(f"🔗 URL: {ws_url}\n")
    
    try:
        async with websockets.connect(ws_url) as ws:
            print("🟢 Connected successfully!")
            print("Type 'exit' or 'quit' to close the connection.\n")
            
            session_id = None
            
            while True:
                # 1. Get user input
                try:
                    user_message = input("\nYou: ")
                except (KeyboardInterrupt, EOFError):
                    print("\n👋 Exiting...")
                    break
                    
                if not user_message.strip():
                    continue
                    
                if user_message.lower() in ["exit", "quit"]:
                    print("👋 Disconnecting...")
                    break
                
                # 2. Build JSON request payload
                payload = {
                    "message": user_message.strip(),
                    "session_id": session_id,
                    "top_k": 10,
                    "max_depth": 2
                }
                
                # Send frame
                await ws.send(json.dumps(payload))
                
                # 3. Listen for streaming response frames
                print("Bot: ", end="", flush=True)
                
                while True:
                    frame_raw = await ws.recv()
                    frame = json.loads(frame_raw)
                    
                    frame_type = frame.get("type")
                    
                    if frame_type == "start":
                        # Capture and maintain session ID across conversation turns
                        if not session_id:
                            session_id = frame.get("session_id")
                            
                    elif frame_type == "sources":
                        # Print grounding metadata chunk before text starts
                        sources = frame.get("sources", [])
                        if sources:
                            print(f"\n[Grounding Sources Verified: {len(sources)} chunks]")
                            for idx, src in enumerate(sources[:3]):
                                score = src.get("score", 0.0)
                                print(f"  • Source #{idx+1} (Match Score: {round(score*100)}%): Chunk {src.get('chunk_id')[:8]}")
                            print("--------------------------------------------------")
                            print("Bot: ", end="", flush=True)
                            
                    elif frame_type == "content":
                        # Stream the token chunk in real-time
                        print(frame.get("delta", ""), end="", flush=True)
                        
                    elif frame_type == "done":
                        # Generation finished
                        print(f"\n\n[Session: {session_id} | Final response saved]")
                        break
                        
                    elif frame_type == "error":
                        print(f"\n❌ Error from server: {frame.get('detail')}")
                        break
                        
    except websockets.exceptions.InvalidURI:
        print("❌ Error: Invalid WebSocket URI. Check agent/tenant values.")
    except websockets.exceptions.ConnectionClosedOK:
        print("🟢 WebSocket closed normally.")
    except Exception as e:
        print(f"\n❌ Connection Error: {e}")

if __name__ == "__main__":
    print("==================================================")
    print("🧠 GraphMind WebSocket Embed Testing Client")
    print("==================================================")
    
    # Port 4915 is currently running in your terminal log
    host = input("Backend Host [default: localhost:4915]: ").strip() or "localhost:4915"
    tenant_id = input("Tenant ID (UUID): ").strip()
    agent_id = input("Agent ID (UUID): ").strip()
    
    if not tenant_id or not agent_id:
        print("❌ Error: Tenant ID and Agent ID are required.")
        sys.exit(1)
        
    # Standardize WS URI
    ws_uri = f"ws://{host}/api/v1/embed/chats/{agent_id}/ws?tenant_id={tenant_id}"
    
    asyncio.run(chat_loop(ws_uri))
