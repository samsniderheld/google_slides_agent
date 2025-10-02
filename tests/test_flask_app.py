import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import sys
import os

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask_app import app, service


class TestFlaskApp(unittest.TestCase):
    
    def setUp(self):
        """Set up test client and mock configurations."""
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['SECRET_KEY'] = 'test-secret-key'
        self.client = self.app.test_client()
        
        # Mock the service to avoid real API calls
        self.service_patcher = patch('flask_app.service')
        self.mock_service = self.service_patcher.start()
        
    def tearDown(self):
        """Clean up after tests."""
        self.service_patcher.stop()
    
    def test_index_route_renders(self):
        """Test that index route renders successfully."""
        with patch.object(service, 'get_user_info', return_value=None):
            response = self.client.get('/')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Google Slides Generator', response.data)
    
    def test_index_route_with_authenticated_user(self):
        """Test index route with authenticated user."""
        mock_user = {'name': 'Test User', 'email': 'test@example.com'}
        with patch.object(service, 'get_user_info', return_value=mock_user):
            response = self.client.get('/')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Test User', response.data)
            self.assertIn(b'test@example.com', response.data)
    
    def test_login_route_redirects_to_auth(self):
        """Test that login route initiates OAuth flow."""
        with patch.object(service, 'get_auth_url', return_value='https://accounts.google.com/oauth/auth'):
            response = self.client.get('/login')
            self.assertEqual(response.status_code, 302)
            self.assertIn('accounts.google.com', response.location)
    
    def test_login_route_handles_auth_error(self):
        """Test login route error handling."""
        with patch.object(service, 'get_auth_url', side_effect=Exception('Auth error')):
            response = self.client.get('/login')
            self.assertEqual(response.status_code, 500)
            data = json.loads(response.data)
            self.assertIn('error', data)
            self.assertIn('Auth error', data['error'])
    
    def test_logout_route_clears_session(self):
        """Test that logout clears session and redirects."""
        with self.client.session_transaction() as sess:
            sess['credentials'] = {'token': 'test-token'}
        
        response = self.client.get('/logout')
        self.assertEqual(response.status_code, 302)
        
        # Check session is cleared
        with self.client.session_transaction() as sess:
            self.assertNotIn('credentials', sess)
    
    def test_oauth_callback_success(self):
        """Test successful OAuth callback handling."""
        with patch.object(service, 'handle_oauth_callback', return_value=Mock()):
            response = self.client.get('/oauth/callback?code=test-code&state=test-state')
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.location.endswith('/'))
    
    def test_oauth_callback_missing_code(self):
        """Test OAuth callback with missing authorization code."""
        response = self.client.get('/oauth/callback?state=test-state')
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('No authorization code received', data['error'])
    
    def test_oauth_callback_handles_error(self):
        """Test OAuth callback error handling."""
        with patch.object(service, 'handle_oauth_callback', side_effect=Exception('OAuth error')):
            response = self.client.get('/oauth/callback?code=test-code&state=test-state')
            self.assertEqual(response.status_code, 500)
            data = json.loads(response.data)
            self.assertIn('OAuth error', data['error'])
    
    def test_create_presentation_success(self):
        """Test successful presentation creation."""
        mock_result = {
            'success': True,
            'message': 'Successfully created presentation with 5/5 slides',
            'url': 'https://docs.google.com/presentation/d/test-id/edit'
        }
        
        with patch.object(service, 'create_presentation_from_concept', return_value=mock_result):
            response = self.client.post('/api/create-presentation',
                                      data=json.dumps({
                                          'concept': 'Test marketing campaign',
                                          'title': 'Test Presentation'
                                      }),
                                      content_type='application/json')
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertTrue(data['success'])
            self.assertIn('5/5 slides', data['message'])
            self.assertIn('docs.google.com', data['url'])
    
    def test_create_presentation_empty_concept(self):
        """Test presentation creation with empty concept."""
        with patch.object(service, 'create_presentation_from_concept', 
                         side_effect=Exception('Please provide a concept')):
            response = self.client.post('/api/create-presentation',
                                      data=json.dumps({
                                          'concept': '',
                                          'title': 'Test Presentation'
                                      }),
                                      content_type='application/json')
            
            self.assertEqual(response.status_code, 500)
            data = json.loads(response.data)
            self.assertFalse(data['success'])
            self.assertIn('Please provide a concept', data['error'])
    
    def test_create_presentation_not_authenticated(self):
        """Test presentation creation without authentication."""
        with patch.object(service, 'create_presentation_from_concept', 
                         side_effect=Exception('Not authenticated')):
            response = self.client.post('/api/create-presentation',
                                      data=json.dumps({
                                          'concept': 'Test concept',
                                          'title': 'Test Presentation'
                                      }),
                                      content_type='application/json')
            
            self.assertEqual(response.status_code, 500)
            data = json.loads(response.data)
            self.assertFalse(data['success'])
            self.assertIn('Not authenticated', data['error'])
    
    def test_create_presentation_missing_data(self):
        """Test presentation creation with missing JSON data."""
        response = self.client.post('/api/create-presentation',
                                  data='invalid json',
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 500)
    
    def test_create_presentation_default_values(self):
        """Test presentation creation uses default values correctly."""
        mock_result = {'success': True, 'message': 'Created', 'url': 'test-url'}
        
        with patch.object(service, 'create_presentation_from_concept', return_value=mock_result) as mock_create:
            response = self.client.post('/api/create-presentation',
                                      data=json.dumps({
                                          'concept': 'Test concept'
                                          # No title provided
                                      }),
                                      content_type='application/json')
            
            self.assertEqual(response.status_code, 200)
            # Verify default title was used
            mock_create.assert_called_once_with('Test concept', 'Generated Presentation')
    
    def test_create_presentation_api_error(self):
        """Test presentation creation with API error."""
        with patch.object(service, 'create_presentation_from_concept', 
                         side_effect=Exception('API rate limit exceeded')):
            response = self.client.post('/api/create-presentation',
                                      data=json.dumps({
                                          'concept': 'Test concept',
                                          'title': 'Test Title'
                                      }),
                                      content_type='application/json')
            
            self.assertEqual(response.status_code, 500)
            data = json.loads(response.data)
            self.assertFalse(data['success'])
            self.assertIn('API rate limit exceeded', data['error'])


class TestSlideGeneratorService(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures."""
        self.service = service
        
        # Mock external dependencies
        self.storage_patcher = patch('flask_app.storage')
        self.mock_storage = self.storage_patcher.start()
        
        self.build_patcher = patch('flask_app.build')
        self.mock_build = self.build_patcher.start()
        
        self.base_agent_patcher = patch('flask_app.BaseAgent')
        self.mock_base_agent = self.base_agent_patcher.start()
        
    def tearDown(self):
        """Clean up after tests."""
        self.storage_patcher.stop()
        self.build_patcher.stop()
        self.base_agent_patcher.stop()
    
    def test_get_auth_url_generates_valid_url(self):
        """Test that get_auth_url generates a valid OAuth URL."""
        with patch('flask_app.Flow') as mock_flow_class:
            mock_flow = Mock()
            mock_flow.authorization_url.return_value = ('https://test-auth-url', 'test-state')
            mock_flow_class.from_client_config.return_value = mock_flow
            
            with patch('flask_app.session', {'oauth_state': None}) as mock_session:
                url = self.service.get_auth_url()
                
                self.assertEqual(url, 'https://test-auth-url')
                mock_flow.authorization_url.assert_called_once_with(
                    access_type='offline',
                    include_granted_scopes='true',
                    prompt='consent'
                )
    
    def test_get_auth_url_error_handling(self):
        """Test get_auth_url error handling."""
        with patch('flask_app.Flow') as mock_flow_class:
            mock_flow_class.from_client_config.side_effect = Exception('Flow error')
            
            with self.assertRaises(Exception) as context:
                self.service.get_auth_url()
            
            self.assertIn('Error generating auth URL', str(context.exception))
    
    def test_handle_oauth_callback_success(self):
        """Test successful OAuth callback handling."""
        with patch('flask_app.Flow') as mock_flow_class:
            mock_flow = Mock()
            mock_credentials = Mock()
            mock_credentials.token = 'test-token'
            mock_credentials.refresh_token = 'test-refresh'
            mock_credentials.token_uri = 'test-uri'
            mock_credentials.client_id = 'test-client-id'
            mock_credentials.client_secret = 'test-secret'
            mock_credentials.scopes = ['test-scope']
            mock_flow.credentials = mock_credentials
            mock_flow_class.from_client_config.return_value = mock_flow
            
            with patch('flask_app.session', {'oauth_state': 'test-state'}) as mock_session:
                result = self.service.handle_oauth_callback('test-code', 'test-state')
                
                self.assertEqual(result, mock_credentials)
                mock_flow.fetch_token.assert_called_once_with(code='test-code')
    
    def test_handle_oauth_callback_invalid_state(self):
        """Test OAuth callback with invalid state parameter."""
        with patch('flask_app.session', {'oauth_state': 'expected-state'}):
            with self.assertRaises(Exception) as context:
                self.service.handle_oauth_callback('test-code', 'wrong-state')
            
            self.assertIn('Invalid state parameter', str(context.exception))
    
    def test_get_credentials_from_session_success(self):
        """Test successful credential retrieval from session."""
        test_creds = {
            'token': 'test-token',
            'refresh_token': 'test-refresh',
            'token_uri': 'test-uri',
            'client_id': 'test-client-id',
            'client_secret': 'test-secret',
            'scopes': ['test-scope']
        }
        
        with patch('flask_app.session', {'credentials': test_creds}):
            with patch('flask_app.Credentials') as mock_creds_class:
                mock_creds = Mock()
                mock_creds_class.return_value = mock_creds
                
                result = self.service.get_credentials_from_session()
                
                self.assertEqual(result, mock_creds)
                mock_creds_class.assert_called_once_with(
                    token='test-token',
                    refresh_token='test-refresh',
                    token_uri='test-uri',
                    client_id='test-client-id',
                    client_secret='test-secret',
                    scopes=['test-scope']
                )
    
    def test_get_credentials_from_session_no_credentials(self):
        """Test credential retrieval when no credentials in session."""
        with patch('flask_app.session', {}):
            result = self.service.get_credentials_from_session()
            self.assertIsNone(result)
    
    def test_get_user_info_success(self):
        """Test successful user info retrieval."""
        mock_credentials = Mock()
        mock_drive_service = Mock()
        mock_about = {
            'user': {
                'displayName': 'Test User',
                'emailAddress': 'test@example.com'
            }
        }
        mock_drive_service.about().get().execute.return_value = mock_about
        
        with patch.object(self.service, 'get_credentials_from_session', return_value=mock_credentials):
            with patch('flask_app.build', return_value=mock_drive_service):
                result = self.service.get_user_info()
                
                self.assertEqual(result['name'], 'Test User')
                self.assertEqual(result['email'], 'test@example.com')
    
    def test_get_user_info_no_credentials(self):
        """Test user info retrieval without credentials."""
        with patch.object(self.service, 'get_credentials_from_session', return_value=None):
            result = self.service.get_user_info()
            self.assertIsNone(result)
    
    def test_get_user_info_api_error(self):
        """Test user info retrieval with API error."""
        mock_credentials = Mock()
        
        with patch.object(self.service, 'get_credentials_from_session', return_value=mock_credentials):
            with patch('flask_app.build', side_effect=Exception('API error')):
                result = self.service.get_user_info()
                self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()