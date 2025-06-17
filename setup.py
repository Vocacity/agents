from setuptools import setup, find_packages

setup(
    name="restaurant-voice-agent",
    version="1.0.0",
    description="Restaurant voice agent with LiveKit and Supabase integration",
    packages=find_packages(),
    install_requires=[
        # LiveKit dependencies
        "livekit-agents[google]~=1.0",
        "python-dotenv>=1.0.0",
        
        # Supabase dependencies
        "supabase>=2.7.0",
        "postgrest>=0.16.0",
        
        # Additional utilities
        "pydantic>=2.0.0",
        "asyncpg>=0.29.0",
        "python-dateutil>=2.8.0",
        "pytz>=2024.1",
    ],
    python_requires=">=3.8",
    author="Restaurant Voice Agent",
    author_email="contact@restaurant-agent.com",
    url="https://github.com/your-username/restaurant-voice-agent",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
) 