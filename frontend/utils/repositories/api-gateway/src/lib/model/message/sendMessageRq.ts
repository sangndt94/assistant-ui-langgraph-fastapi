export interface FrontendTool {
  name: string;
  description?: string;
  parameters: { [key: string]: string };
}

export interface MessageContent {
  type: 'text' | 'image' | 'file' | 'tool-call' | 'tool-result';
  text?: string; // Cho type: text
  image?: string; // Cho type: image
  mimeType?: string; // Cho image hoặc file
  data?: string; // Cho type: file
  toolCallId?: string; // Cho tool-call hoặc tool-result
  toolName?: string; // Cho tool-call hoặc tool-result
  args?: any; // Cho tool-call
  result?: any; // Cho tool-result
  isError?: boolean; // Cho tool-result
  providerMetadata?: any; // Tùy chọn
}

export interface ChatMessage {
  role: 'system' | 'user' | 'assistant' | 'tool';
  content: MessageContent[];
}

export interface SendMessageRequest {
  system?: string;
  tools?: FrontendTool[];
  messages: ChatMessage[];
  user_id?: string; // Giữ lại nếu BE cần
  session_id?: string; // Giữ lại nếu BE cần
  agent?: string; // Giữ lại nếu BE cần
}

export interface SendMessageResponse {
  answer: ChatMessage;
  [key: string]: any; // nếu có thêm field khác
}

export interface DeleteChatRequest {
  session_id: string;
  user_id: string;
  agent: string;
}