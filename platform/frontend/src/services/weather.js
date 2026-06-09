import axios from 'axios';

// Use current origin (port 8080 with nginx) for API requests
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || window.location.origin;

/**
 * Weather API client for communicating with backend weather service
 */
class WeatherClient {
  constructor() {
    this.client = axios.create({
      baseURL: `${API_BASE_URL}/api/v1/weather`,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  /**
   * Get current weather and forecast for Nanjing
   * @returns {Promise<Object>} Weather data including current conditions and forecast
   */
  async getNanjingWeather() {
    try {
      const response = await this.client.get('/nanjing');
      return response.data;
    } catch (error) {
      console.error('Failed to fetch Nanjing weather:', error);
      throw error;
    }
  }

  /**
   * Check weather service health
   * @returns {Promise<Object>} Health check result
   */
  async healthCheck() {
    try {
      const response = await this.client.get('/health');
      return response.data;
    } catch (error) {
      console.error('Weather health check failed:', error);
      throw error;
    }
  }
}

// Export singleton instance
const weatherClient = new WeatherClient();
export default weatherClient;
