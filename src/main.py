import streamlit as st
from vector_store import VectorStore
from trip_planner import TripPlanner
from weather_service import WeatherService
from accommodation_service import AccommodationService
from langchain_google_genai import ChatGoogleGenerativeAI
import os
import csv
from dotenv import load_dotenv
from typing import Tuple, Dict, Optional

# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Function to log data to a CSV file
def log_to_csv(data: Dict[str, str], filename='logs.csv') -> None:
    file_exists = os.path.isfile(filename)
    with open(filename, mode='a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=data.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(data)

# Function to extract location and date from the query using the LLM
def extract_location_and_date(query: str, llm: ChatGoogleGenerativeAI) -> Tuple[Optional[str], Optional[str]]:
    location_prompt = f"Extract the location from this query: '{query}'"
    date_prompt = (
        f"Extract and convert the date from the following query: '{query}'. "
        "If the year is not provided, assume it is 2024. Return the date in the format 'YYYY-MM-DD'."
    )

    location_response = llm.invoke(input=[{"role": "user", "content": location_prompt}])
    location = location_response.content.strip()

    # Check if the extracted location is valid and not empty
    if not location or "The provided query" in location:
        location = None

    date_response = llm.invoke(input=[{"role": "user", "content": date_prompt}])
    date = date_response.content.strip()

    return location, date

# Main function to run the Streamlit app
def main() -> None:
    st.title("🌍 AI Powered Trip Planner")
    
    # Initialize services
    weather_service = WeatherService(api_key="f766bfb7860fcf17ef98142c84b1ade2")
    accommodation_service = AccommodationService(api_key="ad5827c9a1msh3412f736f6d392bp1d0d10jsn83572b92d1a8")
    trip_planner = TripPlanner(weather_service, accommodation_service)
    vector_store = VectorStore(dimension=384)  # Initialize with the correct dimension
    llm = ChatGoogleGenerativeAI(model="gemini-pro", google_api_key=GOOGLE_API_KEY, temperature=0.7, top_p=0.9)

    st.write("Welcome! Ask me to plan a trip or retrieve a saved plan.")

    # Check if the session state has messages, if not, initialize it
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Hi! Ask me to plan a trip or retrieve a saved plan."}]
    
    # Track the last response in the session state
    if "last_response" not in st.session_state:
        st.session_state["last_response"] = None
        st.session_state["last_action"] = None

    # Display the conversation history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # Handle user input
    if prompt := st.chat_input(placeholder="Ask me to plan a trip or retrieve a saved plan..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        # Analyze the user query and generate a response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                analyze_query_prompt = f"Analyze the following user query to determine if they want to create a new trip plan or retrieve a saved plan: '{prompt}'. Respond with 'create' if they want to create a new trip plan, or 'retrieve' if they want to retrieve a saved plan."
                query_analysis = llm.invoke(input=[{"role": "user", "content": analyze_query_prompt}])
                action = query_analysis.content.strip().lower()

                # Log the query analysis
                log_to_csv({
                    "Model Name": "gemini-pro",
                    "LLM Hyperparameters": "temperature=0.7, top_p=0.9",
                    "User Input": prompt,
                    "Full Prompt": analyze_query_prompt,
                    "API Request": "",
                    "API Response": query_analysis.content.strip()
                })

                if action == "create":
                    location, date_range = extract_location_and_date(prompt, llm)
                    if not location or not date_range:
                        response = "Could not extract location or date. Please try again ❗"
                    else:
                        # Fetch weather and accommodation data
                        weather_request = f"Requesting weather for {location} on {date_range}"
                        accommodation_request = f"Requesting accommodation for {location} on {date_range}"
                        weather_response = weather_service.get_forecast(location, date_range)
                        accommodation_response = accommodation_service.get_hotels(location)

                        # Log API requests and responses
                        log_to_csv({
                            "Model Name": "gemini-pro",
                            "LLM Hyperparameters": "temperature=0.7, top_p=0.9",
                            "User Input": prompt,
                            "Full Prompt": analyze_query_prompt,
                            "API Request": weather_request,
                            "API Response": str(weather_response)
                        })
                        log_to_csv({
                            "Model Name": "gemini-pro",
                            "LLM Hyperparameters": "temperature=0.7, top_p=0.9",
                            "User Input": prompt,
                            "Full Prompt": analyze_query_prompt,
                            "API Request": accommodation_request,
                            "API Response": str(accommodation_response)
                        })

                        # Generate the trip plan
                        trip_plan = trip_planner.generate_plan(location, date_range)
                        response = f"**Generated Trip Plan for {location} ({date_range}):**\n{trip_plan}"

                        st.session_state["last_response"] = {
                            "response": response,
                            "trip_plan": trip_plan,
                            "metadata": {"location": location, "date_range": date_range}
                        }

                        # Log the generated plan
                        log_to_csv({
                            "Model Name": "gemini-pro",
                            "LLM Hyperparameters": "temperature=0.7, top_p=0.9",
                            "User Input": prompt,
                            "Full Prompt": analyze_query_prompt,
                            "API Request": "",
                            "API Response": query_analysis.content.strip(),
                            "Generated Plan": response,
                            "Follow-up Question": "",
                            "Favorite Saved": "No"
                        })
                        
                elif action == "retrieve":
                    location, _ = extract_location_and_date(prompt, llm)

                    if not location:
                        response = "No saved record found for this location in the database ❗"
                    else:
                        try:
                            retrieved_trip_plan = vector_store.retrieve_trip_plan(location)
                            response = f"**Retrieved Trip Plan for {location}:**\n{retrieved_trip_plan}"
                        except IndexError:
                            response = f"No matching trip plan found for {location}. Please try a different location."
                            st.session_state["last_response"] = None  # Clear last response since retrieval failed

                        # Log the retrieval attempt
                        log_to_csv({
                            "Model Name": "gemini-pro",
                            "LLM Hyperparameters": "temperature=0.7, top_p=0.9",
                            "User Input": prompt,
                            "Full Prompt": analyze_query_prompt,
                            "API Request": "",
                            "API Response": query_analysis.content.strip(),
                            "Generated Plan": response,
                            "Follow-up Question": "",
                            "Favorite Saved": "No"
                        })

                else:
                    response = "Unable to determine the action from the query. Please try again."
                    st.session_state["last_response"] = {
                        "response": response,
                        "trip_plan": None
                    }

                    # Log the response when action is undetermined
                    log_to_csv({
                        "Model Name": "gemini-pro",
                        "LLM Hyperparameters": "temperature=0.7, top_p=0.9",
                        "User Input": prompt,
                        "Full Prompt": analyze_query_prompt,
                        "API Request": "",
                        "API Response": query_analysis.content.strip(),
                        "Generated Plan": response,
                        "Follow-up Question": "",
                        "Favorite Saved": "No"
                    })

                # Only add to chat history if there is a valid response
                if response:
                    st.write(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})

    # Display Like/Dislike buttons at the bottom of the response
    if st.session_state["last_response"] and st.session_state["last_response"]["trip_plan"]:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("👍 Like"):
                vector_store.add_plan(
                    st.session_state["last_response"]["trip_plan"],
                    metadata=st.session_state["last_response"]["metadata"]
                )
                st.session_state["last_action"] = "✔ Trip plan saved to your favorites!"
                # Log the favorite saved status
                log_to_csv({
                    "Model Name": "gemini-pro",
                    "LLM Hyperparameters": "temperature=0.7, top_p=0.9",
                    "User Input": st.session_state["last_response"]["metadata"],
                    "Full Prompt": "",
                    "API Request": "",
                    "API Response": "",
                    "Generated Plan": st.session_state["last_response"]["trip_plan"],
                    "Follow-up Question": "",
                    "Favorite Saved": "Yes"
                })
        with col2:
            if st.button("👎 Dislike"):
                st.session_state["last_action"] = "✖ Trip plan not saved."
                # Log the dislike status
                log_to_csv({
                    "Model Name": "gemini-pro",
                    "LLM Hyperparameters": "temperature=0.7, top_p=0.9",
                    "User Input": st.session_state["last_response"]["metadata"],
                    "Full Prompt": "",
                    "API Request": "",
                    "API Response": "",
                    "Generated Plan": st.session_state["last_response"]["trip_plan"],
                    "Follow-up Question": "",
                    "Favorite Saved": "No"
                })

    # Show the last action message if available
    if st.session_state["last_action"]:
        st.write(st.session_state["last_action"])

# Entry point of the script
if __name__ == "__main__":
    main()
