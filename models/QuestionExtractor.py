import json
import os
from pathlib import Path

import PyPDF2
import toml
from dotenv import load_dotenv
from google import genai
from google.genai import types
from prompts import EXTRACTION_PROMPT
from pydantic import BaseModel, Field


class SectionSchema(BaseModel):
    """A section with its name and questions/subsections"""

    name: str = Field(..., description="Name of the section")
    questions: list[str] = Field(
        ..., description="List of questions/subsections in this section"
    )


class ExtractedQuestionsSchema(BaseModel):
    """Output containing the sections and their questions"""

    sections: list[SectionSchema] = Field(
        ...,
        description="List of sections, each with a name and a list of questions/subsections",
    )


class QuestionExtractor:
    """Class to extract questions and sections from a text using the Google GenAI API."""    
    def __init__(
        self,
        system_prompt: str,
        api_key: str,
        model: str = "gemini-2.0-flash",
    ):
        """Initialize the QuestionExtractor class.

        Parameters
        ----------
        system_prompt : str
            System prompt to use for the LLM model.
        api_key : str
            API key for the LLM Model API.
        model : str, optional
            LLM model to use, by default "gemini-2.0-flash".
        """        
        self.system_prompt = system_prompt
        self.questions = []
        self.api_key = api_key
        self.model = model
        self.client = genai.Client(api_key=self.api_key)

    def pdf_to_text(self, pdf_path: str) -> str:
        """Convert a PDF file to text.

        Parameters
        ----------
        pdf_path : str
            Path to the PDF form file in which to extract
            the sections and their questions.

        Returns
        -------
        str
            The text extracted from the PDF form file.
        """
        with open(pdf_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            text = " ".join([page.extract_text() for page in reader.pages])
        return text

    def extract_questions(self, text: str) -> ExtractedQuestionsSchema:
        """Extract sections and their questions from a text.

        Parameters
        ----------
        text : str
            The text from which to extract the questions.

        Returns
        -------
        ExtractedQuestionsSchema
            Output containing the sections and their questions.
        """
        response = self.client.models.generate_content(
            model=self.model,
            contents=text,
            config=types.GenerateContentConfig(
                system_instruction=self.system_prompt,
                response_mime_type="application/json",
                response_schema=ExtractedQuestionsSchema,
            ),
        )
        # In order to return python dictionary
        return json.loads(response.text)


def main():
    # Load the environment variables (API key)
    load_dotenv()

    # Load the configuration file
    config = toml.load(Path(__file__).parents[1] / "config.toml")

    question_extractor = QuestionExtractor(
        system_prompt=EXTRACTION_PROMPT,
        api_key=os.environ["GEMINI_API_KEY"],
        model=config["google-genai"]["MODEL_NAME"],
    )

    pdf_text = question_extractor.pdf_to_text(
        pdf_path=config["test-documents"]["FORMULARIO"]
    )

    extracted_questions = question_extractor.extract_questions(text=pdf_text)

    print(extracted_questions["sections"][0])


if __name__ == "__main__":
    main()
