from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import os
import json
import uuid
from typing import Any
from dotenv import load_dotenv

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import Flow
from google.cloud import storage

from agents.base_agent import BaseAgent

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')

class SlideGeneratorService:
    """Flask-based slide generation service."""
    
    def __init__(self):
        """Initialize the service."""
        # OAuth configuration
        self.client_config = {
            "web": {
                "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [os.getenv("REDIRECT_URI")]
            }
        }
        
        self.scopes = [
            'https://www.googleapis.com/auth/presentations',
            'https://www.googleapis.com/auth/drive.file',
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/userinfo.profile',
            'openid',
            'https://www.googleapis.com/auth/userinfo.email'
        ]
        
        # Initialize Google Cloud Storage
        self.storage_client = storage.Client()
        self.bucket_name = "slide_agent_templates"
        
        # Initialize deck creative agent
        self._init_agent()
    
    def _init_agent(self):
        """Initialize the BaseAgent for deck creation."""
        try:
            self.deck_agent = BaseAgent(
                config_file="config_files/deck_creative.yaml",
                llm="gemini", 
                model="gemini-2.5-pro",
                schema_path="config_files/deck_schema.yaml"
            )
        except Exception as e:
            print(f"Warning: Could not initialize deck agent: {e}")
            self.deck_agent = None
    
    def get_auth_url(self):
        """Generate Google OAuth authorization URL."""
        try:
            flow = Flow.from_client_config(
                self.client_config,
                scopes=self.scopes,
                redirect_uri=self.client_config["web"]["redirect_uris"][0]
            )
            
            auth_url, state = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent'
            )
            
            # Store state for validation
            session['oauth_state'] = state
            
            return auth_url
        except Exception as e:
            raise Exception(f"Error generating auth URL: {str(e)}")
    
    def handle_oauth_callback(self, authorization_code: str, state: str):
        """Handle OAuth callback and exchange code for credentials."""
        try:
            # Verify state
            if state != session.get('oauth_state'):
                raise Exception("Invalid state parameter")
            
            flow = Flow.from_client_config(
                self.client_config,
                scopes=self.scopes,
                redirect_uri=self.client_config["web"]["redirect_uris"][0]
            )
            
            # Exchange authorization code for credentials
            flow.fetch_token(code=authorization_code)
            credentials = flow.credentials
            
            # Store credentials in session
            session['credentials'] = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes
            }
            
            return credentials
            
        except Exception as e:
            raise Exception(f"Authentication failed: {str(e)}")
    
    def get_credentials_from_session(self):
        """Get credentials from session."""
        if 'credentials' not in session:
            return None
        
        from google.oauth2.credentials import Credentials
        
        creds_data = session['credentials']
        credentials = Credentials(
            token=creds_data['token'],
            refresh_token=creds_data['refresh_token'],
            token_uri=creds_data['token_uri'],
            client_id=creds_data['client_id'],
            client_secret=creds_data['client_secret'],
            scopes=creds_data['scopes']
        )
        
        return credentials
    
    def get_user_info(self):
        """Get authenticated user information."""
        credentials = self.get_credentials_from_session()
        if not credentials:
            return None
        
        try:
            drive_service = build('drive', 'v3', credentials=credentials)
            about = drive_service.about().get(fields="user").execute()
            user = about.get('user', {})
            return {
                'name': user.get('displayName', 'Unknown'),
                'email': user.get('emailAddress', 'Unknown')
            }
        except Exception as e:
            print(f"Error getting user info: {e}")
            return None
    
    def create_presentation_from_concept(self, concept: str, presentation_title: str):
        """Create a new presentation from a concept."""
        credentials = self.get_credentials_from_session()
        if not credentials:
            raise Exception("Not authenticated")
        
        if not concept or not concept.strip():
            raise Exception("Please provide a concept")
        
        if not self.deck_agent:
            raise Exception("Deck agent not initialized")
        
        try:
            # Generate deck structure
            deck_structure = self.deck_agent.basic_api_call_structured(concept)
            
            # Initialize Google services
            slides_service = build("slides", "v1", credentials=credentials)
            drive_service = build('drive', 'v3', credentials=credentials)
            
            # Copy source presentation (hardcoded template ID)
            source_presentation_id = "1kKzgzXhb4cc_Dn7z1lxui8sIfCan4xqs_Y-xHgzU0vk"
            copy_metadata = {'name': presentation_title or "Generated Presentation"}
            copied_file = drive_service.files().copy(
                fileId=source_presentation_id,
                body=copy_metadata
            ).execute()
            
            copied_presentation_id = copied_file.get('id')
            presentation_url = f"https://docs.google.com/presentation/d/{copied_presentation_id}/edit"
            
            # Process slides
            slides_created = 0
            for i, slide in enumerate(deck_structure.slides):
                try:
                    self._create_slide(slides_service, copied_presentation_id, slide, i)
                    slides_created += 1
                except Exception as e:
                    print(f"Warning: Failed to create slide {i+1}: {e}")
            
            return {
                'success': True,
                'message': f"Successfully created presentation with {slides_created}/{len(deck_structure.slides)} slides",
                'url': presentation_url
            }
            
        except Exception as e:
            raise Exception(f"Error creating presentation: {str(e)}")
    
    def _create_slide(self, slides_service, presentation_id: str, slide: Any, slide_index: int):
        """Create a single slide in the presentation."""
        from create_deck import replace_page_object_ids
        
        # Load slide template from Cloud Storage
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            blob_name = f"{slide.slide_type}.txt"
            blob = bucket.blob(blob_name)
            
            if not blob.exists():
                raise FileNotFoundError(f"Template not found in bucket: {blob_name}")
            
            template_content = blob.download_as_text()
            slide_template_data = json.loads(template_content)
            
        except Exception as e:
            raise Exception(f"Error loading template from Cloud Storage: {str(e)}")
        
        slide_template = slide_template_data['slide']['json_object']
        
        # Apply text content
        text_content_index = 0
        for obj in slide_template['requests']:
            if "replaceAllText" in obj:
                if text_content_index < len(slide.slide_content):
                    obj["replaceAllText"]["replaceText"] = slide.slide_content[text_content_index]
                    text_content_index += 1
        
        # Update slide IDs
        old_id = list(slide_template['requests'][0]['duplicateObject']['objectIds'].items())[0][0]
        new_slide_id = f"NewSlide_{uuid.uuid4().hex[:8]}"
        
        slide_template['requests'][0]['duplicateObject']['objectIds'][old_id] = new_slide_id
        slide_template = replace_page_object_ids(slide_template, old_id, new_slide_id)
        
        # Create the slide
        response = slides_service.presentations().batchUpdate(
            presentationId=presentation_id,
            body=slide_template
        ).execute()
        
        slide_id = response['replies'][0]['duplicateObject']['objectId']
        
        # Position the slide
        insertion_object = {
            "requests": [{
                "updateSlidesPosition": {
                    "slideObjectIds": [slide_id],
                    "insertionIndex": slide_index
                }
            }]
        }
        
        slides_service.presentations().batchUpdate(
            presentationId=presentation_id,
            body=insertion_object
        ).execute()


# Initialize the service
service = SlideGeneratorService()

@app.route('/')
def index():
    """Main page."""
    user_info = service.get_user_info()
    return render_template('index.html', user_info=user_info)

@app.route('/login')
def login():
    """Initiate OAuth login."""
    try:
        auth_url = service.get_auth_url()
        return redirect(auth_url)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/oauth/callback')
def oauth_callback():
    """Handle OAuth callback."""
    try:
        code = request.args.get('code')
        state = request.args.get('state')
        
        if not code:
            return jsonify({'error': 'No authorization code received'}), 400
        
        service.handle_oauth_callback(code, state)
        return redirect(url_for('index'))
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/logout')
def logout():
    """Logout user."""
    session.clear()
    return redirect(url_for('index'))

@app.route('/api/create-presentation', methods=['POST'])
def create_presentation():
    """Create presentation API endpoint."""
    try:
        data = request.get_json()
        
        concept = data.get('concept', '').strip()
        title = data.get('title', 'Generated Presentation')
        
        result = service.create_presentation_from_concept(concept, title)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)