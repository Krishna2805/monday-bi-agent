/**
 * API client helper for communicating with the FastAPI backend
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

/**
 * Send full message history to the backend BI agent endpoint.
 *
 * @param {Array<{role: string, content: string}>} messages
 * @returns {Promise<string>} The agent's natural language response reply
 */
export async function sendChatMessage(messages) {
  try {
    const response = await fetch(`${API_BASE_URL}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ messages }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        errorData.detail || `Server error (status ${response.status})`
      );
    }

    const data = await response.json();
    return data.reply;
  } catch (err) {
    console.error("Failed to connect to BI Agent backend:", err);
    throw err;
  }
}

/**
 * Check backend health status
 */
export async function getBackendHealth() {
  try {
    const response = await fetch(`${API_BASE_URL}/health`);
    if (!response.ok) return null;
    return await response.json();
  } catch {
    return null;
  }
}
