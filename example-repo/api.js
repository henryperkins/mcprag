/**
 * API client for handling HTTP requests
 */

class ApiClient {
    constructor(baseUrl, authToken = null) {
        this.baseUrl = baseUrl;
        this.authToken = authToken;
    }

    /**
     * Set authentication token for requests
     */
    setAuthToken(token) {
        this.authToken = token;
    }

    /**
     * Get default headers for requests
     */
    getHeaders() {
        const headers = {
            'Content-Type': 'application/json'
        };
        
        if (this.authToken) {
            headers['Authorization'] = `Bearer ${this.authToken}`;
        }
        
        return headers;
    }

    /**
     * Make a GET request
     */
    async get(endpoint) {
        try {
            const response = await fetch(`${this.baseUrl}${endpoint}`, {
                method: 'GET',
                headers: this.getHeaders()
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('GET request failed:', error);
            throw error;
        }
    }

    /**
     * Make a POST request
     */
    async post(endpoint, data) {
        try {
            const response = await fetch(`${this.baseUrl}${endpoint}`, {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify(data)
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('POST request failed:', error);
            throw error;
        }
    }

    /**
     * Authenticate user and store token
     */
    async authenticate(username, password) {
        const response = await this.post('/auth/login', {
            username,
            password
        });
        
        if (response.token) {
            this.setAuthToken(response.token);
        }
        
        return response;
    }

    /**
     * Search for code snippets
     */
    async searchCode(query, language = null) {
        const searchParams = { query };
        if (language) {
            searchParams.language = language;
        }
        
        return await this.post('/search', searchParams);
    }
}

// Export for use in other modules
export default ApiClient;
