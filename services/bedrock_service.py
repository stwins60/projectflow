"""
AWS Bedrock AI Service for generating issue content.
Uses Claude models via Amazon Bedrock for intelligent issue generation.
"""
import os
import json
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Bedrock configuration
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
BEDROCK_MODEL_ID = os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-3-sonnet-20240229-v1:0')
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')


def get_bedrock_client():
    """Get AWS Bedrock runtime client."""
    try:
        import boto3
        
        if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
            client = boto3.client(
                'bedrock-runtime',
                region_name=AWS_REGION,
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY
            )
        else:
            # Use default credentials (IAM role, environment, etc.)
            client = boto3.client('bedrock-runtime', region_name=AWS_REGION)
        
        return client
    except ImportError:
        logger.error("boto3 not installed. Install with: pip install boto3")
        return None
    except Exception as e:
        logger.error(f"Failed to create Bedrock client: {e}")
        return None


def generate_issue_content(
    prompt: str,
    issue_type: str = 'task',
    context: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Generate issue content using AWS Bedrock.
    
    Args:
        prompt: User's description of what they want to create
        issue_type: Type of issue (task, bug, feature, story)
        context: Optional additional context (project name, etc.)
    
    Returns:
        Dictionary with generated issue fields or None on failure
    """
    client = get_bedrock_client()
    if not client:
        return None
    
    # Build the system prompt based on issue type
    system_prompts = {
        'task': """You are an expert project manager helping create well-defined tasks.
Generate clear, actionable task descriptions with specific deliverables.""",
        
        'bug': """You are an expert QA engineer helping document bugs.
Generate detailed bug reports with steps to reproduce, expected vs actual behavior, and potential causes.""",
        
        'feature': """You are an expert product manager helping define features.
Generate comprehensive feature specifications with user stories, acceptance criteria, and technical considerations.""",
        
        'story': """You are an expert agile practitioner helping write user stories.
Generate user stories in the format "As a [user], I want [goal] so that [benefit]" with clear acceptance criteria."""
    }
    
    system_prompt = system_prompts.get(issue_type, system_prompts['task'])
    
    # Build the user prompt
    user_prompt = f"""Based on the following description, generate a complete issue for a project management system.

Description: {prompt}
Issue Type: {issue_type}
{f"Project Context: {context}" if context else ""}

Generate a JSON response with the following fields:
- title: A clear, concise title (max 100 chars)
- description: Detailed description of the issue
- acceptance_criteria: Clear acceptance criteria (bullet points)
- technical_requirements: Technical specifications if applicable
- scope: What's in scope and out of scope
- priority: Suggested priority (low, medium, high, critical)
- estimated_effort: Estimated effort (small, medium, large)

Respond ONLY with valid JSON, no additional text."""

    try:
        # Prepare the request for Claude
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2000,
            "system": system_prompt,
            "messages": [
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            "temperature": 0.7
        }
        
        response = client.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            body=json.dumps(request_body),
            contentType='application/json',
            accept='application/json'
        )
        
        # Parse the response
        response_body = json.loads(response['body'].read())
        
        # Extract the generated text
        if 'content' in response_body and len(response_body['content']) > 0:
            generated_text = response_body['content'][0].get('text', '')
            
            # Try to parse as JSON
            try:
                # Clean up the response (remove markdown code blocks if present)
                clean_text = generated_text.strip()
                if clean_text.startswith('```json'):
                    clean_text = clean_text[7:]
                if clean_text.startswith('```'):
                    clean_text = clean_text[3:]
                if clean_text.endswith('```'):
                    clean_text = clean_text[:-3]
                clean_text = clean_text.strip()
                
                result = json.loads(clean_text)
                logger.info(f"Successfully generated issue content for type: {issue_type}")
                return result
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse AI response as JSON: {e}")
                # Return the raw text as description if JSON parsing fails
                return {
                    'title': prompt[:100] if len(prompt) > 100 else prompt,
                    'description': generated_text,
                    'acceptance_criteria': '',
                    'technical_requirements': '',
                    'scope': '',
                    'priority': 'medium',
                    'estimated_effort': 'medium'
                }
        
        logger.error("Empty response from Bedrock")
        return None
        
    except client.exceptions.AccessDeniedException as e:
        logger.error(f"Access denied to Bedrock model: {e}")
        return None
    except client.exceptions.ValidationException as e:
        logger.error(f"Invalid request to Bedrock: {e}")
        return None
    except Exception as e:
        logger.error(f"Error calling Bedrock: {e}")
        return None


def enhance_description(
    current_description: str,
    issue_type: str = 'task'
) -> Optional[str]:
    """
    Enhance an existing issue description using AI.
    
    Args:
        current_description: The current description to enhance
        issue_type: Type of issue
    
    Returns:
        Enhanced description or None on failure
    """
    client = get_bedrock_client()
    if not client:
        return None
    
    prompt = f"""Improve and expand the following {issue_type} description to make it clearer and more actionable.
Keep the original intent but add structure and detail.

Original description:
{current_description}

Respond with only the improved description text, no JSON or additional formatting."""

    try:
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.5
        }
        
        response = client.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            body=json.dumps(request_body),
            contentType='application/json',
            accept='application/json'
        )
        
        response_body = json.loads(response['body'].read())
        
        if 'content' in response_body and len(response_body['content']) > 0:
            return response_body['content'][0].get('text', '').strip()
        
        return None
        
    except Exception as e:
        logger.error(f"Error enhancing description: {e}")
        return None


def suggest_acceptance_criteria(
    title: str,
    description: str,
    issue_type: str = 'feature'
) -> Optional[str]:
    """
    Generate acceptance criteria suggestions based on title and description.
    """
    client = get_bedrock_client()
    if not client:
        return None
    
    prompt = f"""Generate clear acceptance criteria for the following {issue_type}:

Title: {title}
Description: {description}

Provide 3-5 bullet points that define when this work is complete.
Format each criterion as a testable condition starting with a verb.
Respond with only the bullet points, no additional text."""

    try:
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 500,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.6
        }
        
        response = client.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            body=json.dumps(request_body),
            contentType='application/json',
            accept='application/json'
        )
        
        response_body = json.loads(response['body'].read())
        
        if 'content' in response_body and len(response_body['content']) > 0:
            return response_body['content'][0].get('text', '').strip()
        
        return None
        
    except Exception as e:
        logger.error(f"Error generating acceptance criteria: {e}")
        return None


def is_bedrock_configured() -> bool:
    """Check if Bedrock credentials are configured."""
    # Check for explicit credentials or rely on boto3's credential chain
    if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
        return True
    
    # Try to check if default credentials work
    try:
        import boto3
        session = boto3.Session()
        credentials = session.get_credentials()
        return credentials is not None
    except:
        return False
