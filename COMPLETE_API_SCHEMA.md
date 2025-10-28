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

### Design Asset Creation (Frontend Form) - ✅ FRONTEND COMPATIBLE
```javascript
// POST /api/v1/commerce/designs/sell (NEW ENDPOINT - USE THIS FOR FRONTEND)
const sellDesignFormSchema = {
  designName: "string",                    // ✅ Required - Product name (converts to 'name')
  description: "string",                   // ✅ Required - Product description  
  price: "string",                        // ✅ Required - Price as string (auto-converts to Decimal)
  category: "string",                     // ✅ Required - aerospace|automotive|mechanical|architecture|industrial|other
  fileOrigin: "string",                   // ✅ Required - original|modified|commissioned
  licenseType: "string",                  // ✅ Required - commercial|personal|attribution|non-commercial
  originDeclaration: "boolean",           // ✅ Required - true if original work
  qualityAssurance: "boolean",            // ✅ Required - true if quality assured
  technicalSpecs: "string",               // ✅ Optional - Technical specifications
  tags: "string",                         // ✅ Optional - Comma-separated tags
  instructions: "string"                  // ✅ Optional - Usage instructions
};

// ✅ Frontend Success Response Schema
const designAssetResponseSchema = {
  id: "string",                           // UUID
  name: "string",                         // ✅ Converted from designName
  description: "string|null",
  price: "number",                        // ✅ Converted from string to Decimal
  category: "string|null", 
  status: "string",                       // ✅ Auto-set to "active"
  sales: "number",                        // Default 0
  revenue: "number",                      // Default 0.00
  views: "number",                        // Default 0
  likes: "number",                        // Default 0
  seller_id: "number",                    // ✅ Auto-set from JWT token
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
// 1. Sell Design (Frontend Form) - ✅ WORKING ENDPOINT
const sellDesign = async (formData, token) => {
  try {
    const response = await fetch('http://127.0.0.1:8000/api/v1/commerce/designs/sell', {
      method: 'POST',
      headers: getAuthHeaders(token),
      body: JSON.stringify({
        designName: formData.designName,        // ✅ Exact frontend field name
        description: formData.description,
        price: formData.price,                  // ✅ String OK - auto-converts to Decimal
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

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const result = await response.json();
    console.log('✅ Design submitted successfully:', result);
    return result;
    
  } catch (error) {
    console.error('❌ Error submitting design:', error);
    throw error;
  }
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

### ✅ Schema Conversion Rules (FIXED):
1. **designName** → **name** (✅ handled automatically by `/designs/sell` endpoint)
2. **String prices** → **Decimal/number** (✅ auto-converted by backend)
3. **seller_id** → **Auto-set from JWT token** (✅ no frontend action needed)
4. **UUIDs** → **Generated automatically for IDs** (✅ no frontend action needed)
5. **status** → **Auto-set to "active"** (✅ no frontend action needed)

### 🎯 Frontend Action Required:
**ONLY change the API endpoint URL:**
- ❌ Old: `POST /api/v1/commerce/designs` 
- ✅ New: `POST /api/v1/commerce/designs/sell`

**Your existing form data is perfect - no changes needed!**

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

## 🎛️ Dashboard API Endpoints

### 📊 Purchase Management
Purchase management endpoints for user downloads and support.

#### Get User Purchase Details
```
GET /api/v1/purchase-management/my-purchases
Authorization: Bearer {jwt_token}
```

**Response:**
```javascript
{
  "items": [
    {
      "id": 1,
      "user_id": 123,
      "stl_model_id": 456,
      "purchase_date": "2024-01-15T10:30:00Z",
      "purchase_price": 29.99,
      "payment_method": "credit_card",
      "download_count": 3,
      "last_download": "2024-01-20T14:22:00Z",
      "support_status": "resolved",
      "stl_model": {
        "title": "Mechanical Gear",
        "category": "Engineering"
      }
    }
  ],
  "total": 15,
  "page": 1,
  "size": 50
}
```

#### Download Purchased STL File
```
POST /api/v1/purchase-management/download/{purchase_id}
Authorization: Bearer {jwt_token}
```

**Response:**
```javascript
{
  "download_url": "https://storage.example.com/files/model_123.stl",
  "expires_at": "2024-01-21T10:30:00Z",
  "download_count": 4
}
```

#### Submit Support Ticket
```
POST /api/v1/purchase-management/support-ticket
Authorization: Bearer {jwt_token}
Content-Type: application/json

{
  "purchase_id": 123,
  "issue_type": "download_problem",
  "subject": "Cannot download my purchased file",
  "description": "The download link is not working properly",
  "priority": "medium"
}
```

**Response:**
```javascript
{
  "id": 789,
  "ticket_number": "TICK-2024-001",
  "status": "open",
  "created_at": "2024-01-21T15:45:00Z",
  "estimated_resolution": "2024-01-23T15:45:00Z"
}
```

#### Get Support Tickets
```
GET /api/v1/purchase-management/support-tickets
Authorization: Bearer {jwt_token}
```

**Response:**
```javascript
{
  "items": [
    {
      "id": 789,
      "ticket_number": "TICK-2024-001",
      "purchase_id": 123,
      "issue_type": "download_problem",
      "subject": "Cannot download my purchased file",
      "status": "in_progress",
      "priority": "medium",
      "created_at": "2024-01-21T15:45:00Z",
      "updated_at": "2024-01-22T09:15:00Z"
    }
  ],
  "total": 3,
  "page": 1,
  "size": 50
}
```

### 📈 Analytics Dashboard
Comprehensive analytics endpoints for design and user performance tracking.

#### Get Design Analytics
```
GET /api/v1/analytics/design-analytics?period=month&design_id=123
Authorization: Bearer {jwt_token}
```

**Response:**
```javascript
{
  "design_id": 123,
  "period": "month",
  "total_views": 1250,
  "unique_views": 890,
  "total_downloads": 45,
  "total_purchases": 32,
  "revenue_generated": 960.00,
  "average_rating": 4.7,
  "conversion_rate": 3.6,
  "geographic_data": [
    {"country": "United States", "views": 450, "purchases": 12},
    {"country": "Germany", "views": 280, "purchases": 8},
    {"country": "Japan", "views": 220, "purchases": 6}
  ],
  "daily_stats": [
    {"date": "2024-01-01", "views": 42, "downloads": 2, "purchases": 1},
    {"date": "2024-01-02", "views": 38, "downloads": 1, "purchases": 2}
  ]
}
```

#### Get User Analytics
```
GET /api/v1/analytics/user-analytics?period=week
Authorization: Bearer {jwt_token}
```

**Response:**
```javascript
{
  "period": "week",
  "profile_views": 156,
  "total_designs": 12,
  "total_sales": 28,
  "total_revenue": 840.00,
  "follower_count": 245,
  "average_design_rating": 4.5,
  "top_performing_designs": [
    {
      "design_id": 123,
      "title": "Mechanical Gear",
      "views": 890,
      "purchases": 32,
      "revenue": 960.00
    }
  ],
  "engagement_metrics": {
    "likes_received": 89,
    "comments_received": 23,
    "shares": 12
  }
}
```

#### Get Sales Analytics
```
GET /api/v1/analytics/sales?period=month&start_date=2024-01-01&end_date=2024-01-31
Authorization: Bearer {jwt_token}
```

**Response:**
```javascript
{
  "period": "month",
  "total_sales": 156,
  "total_revenue": 4680.00,
  "average_order_value": 30.00,
  "top_selling_designs": [
    {
      "design_id": 123,
      "title": "Mechanical Gear",
      "sales_count": 32,
      "revenue": 960.00
    }
  ],
  "sales_by_category": [
    {"category": "Engineering", "sales": 45, "revenue": 1350.00},
    {"category": "Art", "sales": 38, "revenue": 1140.00}
  ],
  "daily_sales": [
    {"date": "2024-01-01", "sales": 5, "revenue": 150.00},
    {"date": "2024-01-02", "sales": 7, "revenue": 210.00}
  ]
}
```

### 💳 Payment Methods Management
Secure payment method management for users.

#### Get Payment Methods
```
GET /api/v1/payment-methods
Authorization: Bearer {jwt_token}
```

**Response:**
```javascript
{
  "items": [
    {
      "id": 1,
      "type": "credit_card",
      "provider": "stripe",
      "last_four": "4242",
      "expiry_month": 12,
      "expiry_year": 2025,
      "cardholder_name": "John Doe",
      "is_default": true,
      "is_verified": true,
      "created_at": "2024-01-15T10:30:00Z"
    },
    {
      "id": 2,
      "type": "paypal",
      "provider": "paypal",
      "email": "john.doe@example.com",
      "is_default": false,
      "is_verified": true,
      "created_at": "2024-01-10T14:20:00Z"
    }
  ],
  "total": 2
}
```

#### Add Payment Method
```
POST /api/v1/payment-methods
Authorization: Bearer {jwt_token}
Content-Type: application/json

{
  "type": "credit_card",
  "provider": "stripe",
  "card_number": "4242424242424242",
  "expiry_month": 12,
  "expiry_year": 2025,
  "cvc": "123",
  "cardholder_name": "John Doe",
  "billing_address": {
    "street": "123 Main St",
    "city": "New York",
    "state": "NY",
    "postal_code": "10001",
    "country": "US"
  }
}
```

**Response:**
```javascript
{
  "id": 3,
  "type": "credit_card",
  "provider": "stripe",
  "last_four": "4242",
  "expiry_month": 12,
  "expiry_year": 2025,
  "cardholder_name": "John Doe",
  "is_default": false,
  "is_verified": false,
  "verification_required": true,
  "created_at": "2024-01-21T16:45:00Z"
}
```

#### Verify Payment Method
```
POST /api/v1/payment-methods/{payment_method_id}/verify
Authorization: Bearer {jwt_token}
Content-Type: application/json

{
  "verification_code": "123456"
}
```

**Response:**
```javascript
{
  "id": 3,
  "is_verified": true,
  "verified_at": "2024-01-21T17:00:00Z",
  "message": "Payment method verified successfully"
}
```

#### Set Default Payment Method
```
POST /api/v1/payment-methods/{payment_method_id}/set-default
Authorization: Bearer {jwt_token}
```

**Response:**
```javascript
{
  "id": 3,
  "is_default": true,
  "message": "Payment method set as default"
}
```

#### Delete Payment Method
```
DELETE /api/v1/payment-methods/{payment_method_id}
Authorization: Bearer {jwt_token}
```

**Response:**
```javascript
{
  "message": "Payment method deleted successfully"
}
```

#### Get Payout Settings
```
GET /api/v1/payment-methods/payout-settings
Authorization: Bearer {jwt_token}
```

**Response:**
```javascript
{
  "id": 1,
  "method": "bank_transfer",
  "bank_name": "Chase Bank",
  "account_number": "****1234",
  "routing_number": "****5678",
  "account_holder_name": "John Doe",
  "minimum_payout": 25.00,
  "payout_schedule": "weekly",
  "is_verified": true,
  "created_at": "2024-01-15T10:30:00Z"
}
```

#### Update Payout Settings
```
PUT /api/v1/payment-methods/payout-settings
Authorization: Bearer {jwt_token}
Content-Type: application/json

{
  "method": "bank_transfer",
  "bank_name": "Chase Bank",
  "account_number": "1234567890",
  "routing_number": "987654321",
  "account_holder_name": "John Doe",
  "minimum_payout": 50.00,
  "payout_schedule": "monthly"
}
```

### 🛠️ Advanced Tools
Advanced tools for pricing optimization, review management, and promotion campaigns.

#### Get Pricing Suggestions
```
POST /api/v1/advanced-tools/pricing-suggestions
Authorization: Bearer {jwt_token}
Content-Type: application/json

{
  "design_id": 123,
  "category": "Engineering",
  "complexity": "high",
  "file_size_mb": 15.5,
  "print_time_hours": 8.5
}
```

**Response:**
```javascript
{
  "design_id": 123,
  "suggested_price": 35.00,
  "price_range": {
    "min": 25.00,
    "max": 45.00
  },
  "market_analysis": {
    "average_category_price": 32.50,
    "similar_designs_count": 45,
    "competition_level": "medium"
  },
  "factors": [
    {"factor": "High complexity", "impact": "+15%"},
    {"factor": "Large file size", "impact": "+10%"},
    {"factor": "Long print time", "impact": "+5%"}
  ]
}
```

#### Bulk Update Reviews
```
POST /api/v1/advanced-tools/bulk-review-update
Authorization: Bearer {jwt_token}
Content-Type: application/json

{
  "review_ids": [1, 2, 3, 4, 5],
  "action": "mark_helpful",
  "response_template": "Thank you for your feedback!"
}
```

**Response:**
```javascript
{
  "updated_count": 5,
  "failed_count": 0,
  "message": "Reviews updated successfully"
}
```

#### Create Promotion Campaign
```
POST /api/v1/advanced-tools/promotion-campaigns
Authorization: Bearer {jwt_token}
Content-Type: application/json

{
  "name": "Summer Sale 2024",
  "description": "25% off all engineering designs",
  "discount_type": "percentage",
  "discount_value": 25.0,
  "start_date": "2024-06-01T00:00:00Z",
  "end_date": "2024-08-31T23:59:59Z",
  "design_ids": [123, 456, 789],
  "target_audience": "returning_customers",
  "budget": 500.00
}
```

**Response:**
```javascript
{
  "id": 10,
  "name": "Summer Sale 2024",
  "status": "scheduled",
  "designs_count": 3,
  "estimated_reach": 1250,
  "created_at": "2024-05-15T10:30:00Z",
  "campaign_url": "https://example.com/campaign/summer-sale-2024"
}
```

#### Get Promotion Campaigns
```
GET /api/v1/advanced-tools/promotion-campaigns
Authorization: Bearer {jwt_token}
```

**Response:**
```javascript
{
  "items": [
    {
      "id": 10,
      "name": "Summer Sale 2024",
      "status": "active",
      "discount_type": "percentage",
      "discount_value": 25.0,
      "start_date": "2024-06-01T00:00:00Z",
      "end_date": "2024-08-31T23:59:59Z",
      "designs_count": 3,
      "total_uses": 45,
      "revenue_generated": 1125.00,
      "created_at": "2024-05-15T10:30:00Z"
    }
  ],
  "total": 8,
  "page": 1,
  "size": 50
}
```

#### Update Promotion Campaign
```
PUT /api/v1/advanced-tools/promotion-campaigns/{campaign_id}
Authorization: Bearer {jwt_token}
Content-Type: application/json

{
  "name": "Extended Summer Sale 2024",
  "discount_value": 30.0,
  "end_date": "2024-09-15T23:59:59Z",
  "budget": 750.00
}
```

**Response:**
```javascript
{
  "id": 10,
  "name": "Extended Summer Sale 2024",
  "discount_value": 30.0,
  "end_date": "2024-09-15T23:59:59Z",
  "updated_at": "2024-07-01T14:20:00Z",
  "message": "Campaign updated successfully"
}
```

#### Delete Promotion Campaign
```
DELETE /api/v1/advanced-tools/promotion-campaigns/{campaign_id}
Authorization: Bearer {jwt_token}
```

**Response:**
```javascript
{
  "message": "Promotion campaign deleted successfully"
}
```

### 🏪 Enhanced Sales Management
Extended sales management endpoints integrated with commerce system.

#### Edit Design Details
```
PUT /api/v1/commerce/designs/{design_id}/edit
Authorization: Bearer {jwt_token}
Content-Type: application/json

{
  "title": "Updated Mechanical Gear v2",
  "description": "Improved version with better tolerances",
  "price": 35.00,
  "category": "Engineering",
  "tags": ["mechanical", "gear", "engineering", "precision"],
  "is_featured": true
}
```

**Response:**
```javascript
{
  "id": 123,
  "title": "Updated Mechanical Gear v2",
  "price": 35.00,
  "is_featured": true,
  "updated_at": "2024-01-21T16:45:00Z",
  "message": "Design updated successfully"
}
```

#### Promote Design
```
POST /api/v1/commerce/designs/{design_id}/promote
Authorization: Bearer {jwt_token}
Content-Type: application/json

{
  "promotion_type": "featured",
  "duration_days": 30,
  "budget": 100.00,
  "target_audience": "engineering_enthusiasts"
}
```

**Response:**
```javascript
{
  "design_id": 123,
  "promotion_id": "PROMO-2024-001",
  "status": "active",
  "expires_at": "2024-02-21T16:45:00Z",
  "estimated_reach": 5000,
  "cost": 100.00
}
```

#### Get Design Performance
```
GET /api/v1/commerce/designs/{design_id}/performance?days=30
Authorization: Bearer {jwt_token}
```

**Response:**
```javascript
{
  "design_id": 123,
  "period_days": 30,
  "views": 1250,
  "downloads": 45,
  "purchases": 32,
  "revenue": 960.00,
  "rating": 4.7,
  "reviews_count": 23,
  "conversion_rate": 2.56,
  "trending_score": 8.5,
  "rank_in_category": 3
}
```

## 🔧 Dashboard Schema Models

### Purchase Details Model
```javascript
{
  "id": "integer",
  "user_id": "integer",
  "stl_model_id": "integer", 
  "purchase_date": "datetime",
  "purchase_price": "decimal",
  "payment_method": "string",
  "download_count": "integer",
  "last_download": "datetime",
  "support_status": "string" // pending, in_progress, resolved, closed
}
```

### Support Ticket Model
```javascript
{
  "id": "integer",
  "purchase_id": "integer",
  "user_id": "integer",
  "issue_type": "string", // download_problem, quality_issue, refund_request, other
  "subject": "string",
  "description": "text",
  "status": "string", // open, in_progress, resolved, closed
  "priority": "string", // low, medium, high, urgent
  "created_at": "datetime",
  "updated_at": "datetime",
  "resolved_at": "datetime"
}
```

### Design Analytics Model
```javascript
{
  "id": "integer",
  "design_id": "integer",
  "user_id": "integer",
  "date": "date",
  "views": "integer",
  "unique_views": "integer", 
  "downloads": "integer",
  "purchases": "integer",
  "revenue": "decimal",
  "conversion_rate": "decimal",
  "average_rating": "decimal"
}
```

### User Analytics Model  
```javascript
{
  "id": "integer",
  "user_id": "integer",
  "date": "date",
  "profile_views": "integer",
  "total_designs": "integer",
  "total_sales": "integer",
  "total_revenue": "decimal",
  "follower_count": "integer",
  "following_count": "integer",
  "engagement_score": "decimal"
}
```

### Payment Method Model
```javascript
{
  "id": "integer",
  "user_id": "integer",
  "type": "string", // credit_card, debit_card, paypal, bank_transfer
  "provider": "string", // stripe, paypal, square
  "last_four": "string",
  "expiry_month": "integer",
  "expiry_year": "integer", 
  "cardholder_name": "string",
  "billing_address": "json",
  "is_default": "boolean",
  "is_verified": "boolean",
  "created_at": "datetime"
}
```

### Payout Settings Model
```javascript
{
  "id": "integer",
  "user_id": "integer",
  "method": "string", // bank_transfer, paypal, stripe
  "account_details": "json", // encrypted account information
  "minimum_payout": "decimal",
  "payout_schedule": "string", // daily, weekly, monthly
  "is_verified": "boolean",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### Promotion Campaign Model
```javascript
{
  "id": "integer",
  "user_id": "integer", 
  "name": "string",
  "description": "text",
  "discount_type": "string", // percentage, fixed_amount
  "discount_value": "decimal",
  "start_date": "datetime",
  "end_date": "datetime",
  "design_ids": "json", // array of design IDs
  "target_audience": "string",
  "budget": "decimal",
  "total_uses": "integer",
  "revenue_generated": "decimal",
  "status": "string", // draft, scheduled, active, paused, expired
  "created_at": "datetime"
}
```

## 🎯 Dashboard Integration Notes

### Authentication Requirements
All Dashboard endpoints require JWT authentication with appropriate user permissions.

### Rate Limiting
- Analytics endpoints: 100 requests per hour
- Payment methods: 50 requests per hour  
- Advanced tools: 200 requests per hour
- Purchase management: 1000 requests per hour

### Error Responses
```javascript
// Validation Error
{
  "detail": "Validation failed",
  "errors": [
    {
      "field": "price",
      "message": "Price must be greater than 0"
    }
  ]
}

// Authorization Error
{
  "detail": "Not authorized to access this resource"
}

// Not Found Error
{
  "detail": "Resource not found"
}
```

### Pagination Parameters
```javascript
// Query parameters for paginated endpoints
{
  "page": 1,        // Page number (default: 1)
  "size": 50,       // Items per page (default: 50, max: 100)
  "sort": "created_at", // Sort field
  "order": "desc"   // Sort order: asc, desc
}
```

This comprehensive Dashboard API documentation provides complete integration specifications for all new functionality including purchase management, analytics, payment methods, and advanced tools!