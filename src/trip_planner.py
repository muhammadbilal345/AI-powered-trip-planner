import os
from typing import Dict, Any, List
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from weather_service import WeatherService
from accommodation_service import AccommodationService
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

class TripPlanner:
    def __init__(self, weather_service: WeatherService, accommodation_service: AccommodationService):
        self.weather_service = weather_service
        self.accommodation_service = accommodation_service
        self.llm = ChatGoogleGenerativeAI(model="gemini-pro", google_api_key=GOOGLE_API_KEY, temperature=0.7, top_p=0.9)
    
    def generate_location_overview(self, location: str) -> str:
        # Load the location overview prompt from markdown
        with open('prompts/location_overview_prompt.md', 'r') as file:
            location_overview_prompt = file.read()

        location_overview_prompt = ("# Please ensure the response is friendly and conversational. Also ensure not to include this line in response\n" 
                                    + location_overview_prompt)
        # Create a prompt template
        prompt_template = PromptTemplate(
            input_variables=["location"],
            template=location_overview_prompt,
        )

        # Create the chain
        chain = LLMChain(llm=self.llm, prompt=prompt_template)

        # Run the chain to generate the location overview
        location_overview = chain.run(location=location)
        
        return location_overview

    def generate_plan(self, location: str, date: str) -> str:
        def format_weather(weather: Dict[str, Any]) -> str:
            return f"On {weather['date']} in {weather['location']}, the temperature will be {weather['temperature']}°C with {weather['description']}."

        def format_hotels(hotels: List[str]) -> str:
            return "\n".join(hotels)
        
        weather = self.weather_service.get_forecast(location, date)
        hotels = self.accommodation_service.get_hotels(location)
        location_overview = self.generate_location_overview(location)

        formatted_weather = format_weather(weather)
        formatted_hotels = format_hotels(hotels)

        # Load the trip plan prompt from markdown
        with open('prompts/trip_plan_prompt.md', 'r') as file:
            trip_plan_prompt = file.read()

        # Add explicit instruction for human tone and format preservation at the start
        trip_plan_prompt = ("# Please follow the provided format and ensure the response is friendly and conversational. Ensure to keep same format for suggested journey. Also ensure not to include this line in response\n" 
                            + trip_plan_prompt)

        # Create a prompt template
        prompt_template = PromptTemplate(
            input_variables=["location", "location_overview", "weather", "hotels"],
            template=trip_plan_prompt,
        )

        # Create the chain
        chain = LLMChain(llm=self.llm, prompt=prompt_template)

        # Run the chain
        trip_plan = chain.run(location=location, location_overview=location_overview, weather=formatted_weather, hotels=formatted_hotels)

        return trip_plan
