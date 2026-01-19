import requests
import json

url = "http://localhost:8000/api/v1/volumes/f08c7390-87e7-4d62-b655-1ac258fe4bf8"
headers = {
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsImtpZCI6InppR25HK29WMk9wZENRQk8iLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL2ZienJvYmdzdHdreHdjc29tdHVyLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiI3NWRhZGJiYy0zNGRhLTRjYjMtYTc1ZC1lZGFhNWRjZjczNDEiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzYzODYzMzY5LCJpYXQiOjE3NjM4NTk3NjksImVtYWlsIjoiamFjb2IuZWNvbW1lcmNlQGdtYWlsLmNvbSIsInBob25lIjoiIiwiYXBwX21ldGFkYXRhIjp7InByb3ZpZGVyIjoiZW1haWwiLCJwcm92aWRlcnMiOlsiZW1haWwiLCJnb29nbGUiXX0sInVzZXJfbWV0YWRhdGEiOnsiYXZhdGFyX3VybCI6Imh0dHBzOi8vbGgzLmdvb2dsZXVzZXJjb250ZW50LmNvbS9hL0FDZzhvY0tidUxXMUZueUF4anlKb2d5VmY0RXFEUXJxNHNyaEoyb0U1QjF6bkM0QlBnenYyM2c9czk2LWMiLCJlbWFpbCI6ImphY29iLmVjb21tZXJjZUBnbWFpbC5jb20iLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwiZnVsbF9uYW1lIjoiSmFjb2IgRWxsaW90dCIsImlzcyI6Imh0dHBzOi8vYWNjb3VudHMuZ29vZ2xlLmNvbSIsIm5hbWUiOiJKYWNvYiBFbGxpb3R0IiwicGhvbmVfdmVyaWZpZWQiOmZhbHNlLCJwaWN0dXJlIjoiaHR0cHM6Ly9saDMuZ29vZ2xldXNlcmNvbnRlbnQuY29tL2EvQUNnOG9jS2J1TFcxRm55QXhqeUpvZ3lWZjRFcURRcnE0c3JoSjJvRTVCMXpuQzRCUGd6djIzZz1zOTYtYyIsInByb3ZpZGVyX2lkIjoiMTA0NjYxNzQwOTY1MTQ3OTc1OTExIiwic3ViIjoiMTA0NjYxNzQwOTY1MTQ3OTc1OTExIn0sInJvbGUiOiJhdXRoZW50aWNhdGVkIiwiYWFsIjoiYWFsMSIsImFtciI6W3sibWV0aG9kIjoib2F1dGgiLCJ0aW1lc3RhbXAiOjE3NjM4NDIyMDF9XSwic2Vzc2lvbl9pZCI6IjBiYmYyYjA3LWIwY2MtNGY5ZC04MzI4LWEzM2RmZDY0YzFkZiIsImlzX2Fub255bW91cyI6ZmFsc2V9.ZSaOidDGFJu5ad4AIC-pzZWO1Mbt--ta6aOXE_6_6hTtQ"
}

try:
    response = requests.get(url, headers=headers)
    print(f"Status Code: {response.status_code}")
    if response.ok:
        data = response.json()
        # Print top-level keys
        print("Keys:", data.keys())
        # Check outline specifically
        print("Outline:", str(data.get('outline'))[:100] + "...")
        print("Graph Structure (if exists):", str(data.get('graph_structure'))[:100] + "...")
    else:
        print(response.text)
except Exception as e:
    print(e)