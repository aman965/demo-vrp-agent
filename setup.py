from setuptools import setup, find_packages

setup(
    name="vrp-app",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "streamlit>=1.32.0",
        "pandas>=2.2.0",
        "numpy>=1.26.3",
        "plotly>=5.18.0",
        "folium>=0.15.1",
        "streamlit-folium>=0.15.1",
        "openai>=1.12.0",
        "ortools>=9.8.3296",
    ],
) 