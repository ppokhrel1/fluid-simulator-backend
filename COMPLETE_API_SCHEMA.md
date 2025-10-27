# Complete Backend API Schema Documentation

## 🎯 Base Configuration
```javascript
const API_CONFIG = {
  baseURL: 'http://127.0.0.1:8000',
  endpoints: {
    auth: '/api/v1',
    commerce: '/api/v1/commerce', 
    chat: '/api/v1/chat',
    labels: '/api/v1/labels',
    models: '/api/v1'
  }
};

const getAuthHeaders = (token) => ({
  'Content-Type': 'application/json',
  'Authorization': `Bearer ${token}`,
  'Accept': 'application/json'
});
```

## 🔐 Authentication Schemas

### User Registration (Frontend Compatible)
```javascript
// POST /api/v1/register
const registrationSchema = {
  username: "string",           // Required, 20 chars max
  email: "string",             // Required, valid email
  password: "string",          // Required
  full_name: "string"          // Required (maps to 'name' in database)
};

// Response Schema
const userResponseSchema = {
  id: "number",
  email: "string", 
  full_name: "string",
  is_superuser: "boolean",
  is_active: "boolean",
  profile_image_url: "string",
  tier_id: "number|null"
};
```

### User Login
```javascript  
// POST /api/v1/login (FormData)
const loginSchema = {
  username: "string",          // FormData field
  password: "string"           // FormData field
};

// Response Schema
const loginResponseSchema = {
  access_token: "string",      // JWT token
  token_type: "bearer"
};
```

## 🛒 Commerce System Schemas

### Design Asset Creation (Frontend Form)
```javascript
// POST /api/v1/commerce/designs/sell (NEW ENDPOINT FOR FRONTEND)
const sellDesignFormSchema = {
  designName: "string",                    // Required - Product name
  description: "string",                   // Required - Product description  
  price: "string",                        // Required - Price as string (will be converted)
  category: "string",                     // Required - aerospace|automotive|mechanical|architecture|industrial|other
  fileOrigin: "string",                   // Required - original|modified|commissioned
  licenseType: "string",                  // Required - commercial|personal|attribution|non-commercial
  originDeclaration: "boolean",           // Required - true if original work
  qualityAssurance: "boolean",            // Required - true if quality assured
  technicalSpecs: "string",               // Optional - Technical specifications
  tags: "string",                         // Optional - Comma-separated tags
  instructions: "string"                  // Optional - Usage instructions
};

// Response Schema
const designAssetResponseSchema = {
  id: "string",                           // UUID
  name: "string",
  description: "string|null",
  price: "number",                        // Decimal converted to number
  category: "string|null", 
  status: "string",                       // active|draft|sold|paused
  sales: "number",                        // Default 0
  revenue: "number",                      // Default 0.00
  views: "number",                        // Default 0
  likes: "number",                        // Default 0
  seller_id: "number",
  original_model_id: "number|null",
  created_at: "string",                   // ISO datetime
  updated_at: "string"                    // ISO datetime
};
```

### Alternative Design Creation (Direct API)
```javascript
// POST /api/v1/commerce/designs (DIRECT API)
const designAssetCreateSchema = {
  name: "string",                         // Required
  description: "string|null",             // Optional
  price: "number",                        // Required - Decimal/number
  category: "string|null",                // Optional
  status: "string",                       // Optional - Default "draft"
  seller_id: "number",                    // Required (auto-set from auth)
  original_model_id: "number|null"        // Optional
};
```

### Shopping Cart Operations
```javascript
// POST /api/v1/commerce/cart
const cartItemCreateSchema = {
  design_id: "string",                    // Required - UUID of design
  name: "string",                         // Required - Item name
  price: "number",                        // Required - Item price
  original_price: "number|null",          // Optional - Original price if discounted
  size: "string",                         // Required - S|M|L|XL|Custom
  color: "string",                        // Required - Color option
  icon: "string",                         // Required - Icon URL or identifier
  quantity: "number"                      // Optional - Default 1
};

// GET /api/v1/commerce/cart - Response Schema
const cartItemResponseSchema = {
  id: "string",                           // UUID
  user_id: "number",
  design_id: "string",
  name: "string",
  price: "number",
  original_price: "number|null",
  size: "string",
  color: "string", 
  icon: "string",
  quantity: "number",
  added_at: "string"                      // ISO datetime
};

// PUT /api/v1/commerce/cart/{cart_item_id}
const cartItemUpdateSchema = {
  quantity: "number|null",                // Optional
  size: "string|null",                    // Optional
  color: "string|null"                    // Optional
};
```

### Checkout & Sales
```javascript
// POST /api/v1/commerce/checkout
// No body required - processes entire cart for authenticated user

// Response Schema
const checkoutResponseSchema = {
  success: "boolean",
  message: "string",
  transaction_ids: "string[]",            // Array of created transaction UUIDs
  total_amount: "number"
};

// GET /api/v1/commerce/sales/purchases - Response Schema
const salesTransactionResponseSchema = {
  id: "string",                           // UUID
  design_id: "string",
  design_name: "string",
  buyer_id: "number",
  buyer_email: "string", 
  price: "number",
  seller_earnings: "number",
  date: "string",                         // ISO datetime
  status: "string",                       // completed|pending|refunded
  transaction_id: "string|null",
  commission_rate: "number"               // Default 0.10 (10%)
};
```

### Payout System
```javascript
// POST /api/v1/commerce/payouts
const payoutCreateSchema = {
  amount: "number",                       // Required - Amount to payout
  method: "string",                       // Required - paypal|stripe|bank_transfer
  fees: "number",                         // Optional - Default 0.00
  net_amount: "number",                   // Required - Amount after fees
  payout_account: "string|null"           // Optional - Account identifier
};

// Response Schema
const payoutResponseSchema = {
  id: "string",                           // UUID
  seller_id: "number",
  amount: "number",
  method: "string",
  fees: "number",
  net_amount: "number",
  payout_account: "string|null",
  status: "string",                       // pending|processing|completed|failed
  request_date: "string",                 // ISO datetime
  processed_date: "string|null"          // ISO datetime or null
};
```

## 🤖 AI Chatbot System Schemas

### Chat Session Management
```javascript
// POST /api/v1/chat/sessions
const chatSessionCreateSchema = {
  model_id: "number|null"                 // Optional - Link to 3D model
};

// Response Schema
const chatSessionResponseSchema = {
  id: "string",                           // UUID
  user_id: "number",
  model_id: "number|null",
  created_at: "string",                   // ISO datetime
  updated_at: "string"                    // ISO datetime
};
```

### Chat Messages
```javascript
// POST /api/v1/chat/sessions/{session_id}/messages
const chatMessageCreateSchema = {
  message: "string",                      // Required - User message
  message_type: "string"                  // Optional - Default "text"
};

// Response Schema
const chatMessageResponseSchema = {
  session_id: "string",                   // UUID
  user_message: {
    id: "string",                         // UUID
    session_id: "string",
    message_type: "string",               // user|assistant
    content: "string",
    timestamp: "string"                   // ISO datetime
  },
  ai_response: {
    id: "string",                         // UUID
    session_id: "string", 
    message_type: "string",               // user|assistant
    content: "string",
    timestamp: "string"                   // ISO datetime
  },
  message: "string"                       // Success message
};

// GET /api/v1/chat/sessions/{session_id}/messages
const chatHistoryResponseSchema = {
  id: "string",                           // UUID
  session_id: "string",
  message_type: "string",                 // user|assistant
  content: "string",
  file_name: "string|null",
  file_data: "string|null",
  timestamp: "string"                     // ISO datetime
};
```

## 🏷️ 3D Model Labeling System Schemas

### Label Creation
```javascript
// POST /api/v1/labels/models/{model_id}/labels
const assetLabelCreateSchema = {
  position_x: "number",                   // Required - X coordinate
  position_y: "number",                   // Required - Y coordinate  
  position_z: "number",                   // Required - Z coordinate
  text: "string",                         // Required - Label text
  category: "string"                      // Optional - Material|Part|Function|Texture|Dimension|Other
};

// Response Schema
const assetLabelResponseSchema = {
  id: "string",                           // UUID
  model_id: "number",
  position_x: "number",
  position_y: "number",
  position_z: "number",
  text: "string",
  category: "string|null",
  created_by: "number",
  created_at: "string",                   // ISO datetime
  updated_at: "string"                    // ISO datetime
};

// PUT /api/v1/labels/labels/{label_id}
const assetLabelUpdateSchema = {
  position_x: "number|null",              // Optional
  position_y: "number|null",              // Optional
  position_z: "number|null",              // Optional
  text: "string|null",                    // Optional
  category: "string|null"                 // Optional
};
```

### AI Label Suggestions
```javascript
// POST /api/v1/labels/models/{model_id}/ai-suggestions
// No body required

// Response Schema
const aiLabelSuggestionSchema = {
  label_text: "string",
  category: "string", 
  confidence: "number",                   // 0.0 to 1.0
  suggested_position: {
    x: "number",
    y: "number", 
    z: "number"
  },
  description: "string"
};
```

## 📁 File Upload Schema (STL Models)

### STL File Upload
```javascript
// POST /api/v1/upload_stl (FormData)
const stlUploadSchema = {
  file: "File",                           // Required - STL file
  name: "string",                         // Required - Model name
  description: "string",                  // Optional - Model description
  project_name: "string",                 // Optional
  designer: "string",                     // Optional
  tags: "string[]"                        // Optional - Array of tags
};

// Response Schema  
const uploadedModelResponseSchema = {
  id: "string",                           // UUID
  name: "string",
  file_name: "string",
  file_path: "string",
  file_size: "string",
  file_type: "string",
  description: "string|null",
  web_link: "string|null",
  tags: "string[]",
  thumbnail: "string|null",
  project_name: "string|null",
  designer: "string|null",
  created_by_user_id: "number",
  created_at: "string",                   // ISO datetime
  updated_at: "string"                    // ISO datetime
};
```

## 🚫 Error Response Schema

```javascript
const errorResponseSchema = {
  detail: "string|object",                // Error message or validation details
  status_code: "number"                   // HTTP status code
};

// Common HTTP Status Codes:
// 200 - Success
// 201 - Created  
// 400 - Bad Request (validation error)
// 401 - Unauthorized (missing/invalid token)
// 403 - Forbidden (insufficient permissions)  
// 404 - Not Found
// 422 - Unprocessable Entity (validation error)
// 500 - Internal Server Error
```

## 🔧 Complete API Call Examples

### Authentication Flow
```javascript
// 1. Register User
const registerUser = async (userData) => {
  const response = await fetch('http://127.0.0.1:8000/api/v1/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      username: userData.username,
      email: userData.email, 
      password: userData.password,
      full_name: userData.fullName
    })
  });
  return response.json();
};

// 2. Login User
const loginUser = async (credentials) => {
  const formData = new FormData();
  formData.append('username', credentials.username);
  formData.append('password', credentials.password);
  
  const response = await fetch('http://127.0.0.1:8000/api/v1/login', {
    method: 'POST',
    body: formData
  });
  return response.json();
};
```

### Commerce Flow
```javascript
// 1. Sell Design (Frontend Form)
const sellDesign = async (formData, token) => {
  const response = await fetch('http://127.0.0.1:8000/api/v1/commerce/designs/sell', {
    method: 'POST',
    headers: getAuthHeaders(token),
    body: JSON.stringify({
      designName: formData.designName,
      description: formData.description,
      price: formData.price,            // String OK - will be converted
      category: formData.category,
      fileOrigin: formData.fileOrigin,
      licenseType: formData.licenseType,
      originDeclaration: formData.originDeclaration,
      qualityAssurance: formData.qualityAssurance,
      technicalSpecs: formData.technicalSpecs || '',
      tags: formData.tags || '',
      instructions: formData.instructions || ''
    })
  });
  return response.json();
};

// 2. Add to Cart
const addToCart = async (cartItem, token) => {
  const response = await fetch('http://127.0.0.1:8000/api/v1/commerce/cart', {
    method: 'POST',
    headers: getAuthHeaders(token),
    body: JSON.stringify({
      design_id: cartItem.designId,
      name: cartItem.name,
      price: cartItem.price,           // Number required
      size: cartItem.size,
      color: cartItem.color,
      icon: cartItem.icon,
      quantity: cartItem.quantity || 1
    })
  });
  return response.json();
};

// 3. Checkout
const checkout = async (token) => {
  const response = await fetch('http://127.0.0.1:8000/api/v1/commerce/checkout', {
    method: 'POST',
    headers: getAuthHeaders(token)
  });
  return response.json();
};
```

### Chat Flow
```javascript
// 1. Create Chat Session
const createChatSession = async (modelId, token) => {
  const response = await fetch('http://127.0.0.1:8000/api/v1/chat/sessions', {
    method: 'POST',
    headers: getAuthHeaders(token),
    body: JSON.stringify({
      model_id: modelId || null
    })
  });
  return response.json();
};

// 2. Send Message
const sendMessage = async (sessionId, message, token) => {
  const response = await fetch(`http://127.0.0.1:8000/api/v1/chat/sessions/${sessionId}/messages`, {
    method: 'POST',
    headers: getAuthHeaders(token),
    body: JSON.stringify({
      message: message,
      message_type: 'text'
    })
  });
  return response.json();
};
```

### Labeling Flow
```javascript
// 1. Create Label
const createLabel = async (modelId, labelData, token) => {
  const response = await fetch(`http://127.0.0.1:8000/api/v1/labels/models/${modelId}/labels`, {
    method: 'POST',
    headers: getAuthHeaders(token),
    body: JSON.stringify({
      position_x: labelData.position[0],
      position_y: labelData.position[1],
      position_z: labelData.position[2],
      text: labelData.text,
      category: labelData.category
    })
  });
  return response.json();
};

// 2. Get AI Suggestions
const getAISuggestions = async (modelId, token) => {
  const response = await fetch(`http://127.0.0.1:8000/api/v1/labels/models/${modelId}/ai-suggestions`, {
    method: 'POST',
    headers: getAuthHeaders(token)
  });
  return response.json();
};
```

## 📋 Key Points for Frontend Integration

### ✅ Critical Requirements:
1. **Authentication**: All protected endpoints require `Authorization: Bearer {token}` header
2. **Content-Type**: Always use `application/json` for JSON requests
3. **CORS**: Backend allows all origins, methods, and headers in development
4. **Base URL**: Always use `http://127.0.0.1:8000` (not localhost:3000)

### ✅ Schema Conversion Rules:
1. **designName** → **name** (handled by `/designs/sell` endpoint)
2. **String prices** → **Decimal/number** (auto-converted)
3. **seller_id** → **Auto-set from authenticated user**
4. **UUIDs** → **Generated automatically for IDs**

### ✅ Error Handling:
```javascript
const handleAPIError = async (response) => {
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `HTTP ${response.status}`);
  }
  return response.json();
};
```

This complete schema documentation should allow your frontend chatbot to generate perfectly compatible API calls for your backend!