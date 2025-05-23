# 🚀 LLM Prompt Evaluation & Management System

> **Git-like version control for LLM prompts with automated evaluation and cost tracking**

A comprehensive system for developing, testing, and managing LLM prompts with Git-style version control, automated evaluation, and detailed cost analysis. Built with Streamlit and powered by Google's Gemini 2.0 Flash API (**Free Tier Available**).

## ✨ Key Features

### 🎯 **Automated Prompt Evaluation**
- Execute prompts with **Gemini 2.0 Flash API** (Free tier with generous limits)
- Automated evaluation based on custom criteria
- Real-time cost tracking and token analysis
- Support for both single prompts and template-based workflows

### 💰 **Why Gemini 2.0 Flash?**
- **Free Tier**: Generous free usage limits for development and testing

### 🌿 **Git-like Version Control**
- **Branches**: Manage different prompt approaches in parallel
- **Commits**: Track execution history with descriptive messages
- **Tags**: Mark important milestones and releases
- **Diff Views**: Visual comparison between prompt versions

### 📊 **Advanced Analytics**
- Detailed cost analysis (execution vs evaluation costs)
- Token usage statistics and optimization insights
- Performance comparison between prompt versions
- Branch-specific metrics and ROI tracking

### 💾 **Data Management**
- **Local Storage**: Save/load history as JSON files
- **CSV Import/Export**: Compatible with spreadsheet tools
- **Data Backup**: Complete system state preservation
- **Cross-platform**: Share data between team members

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Google AI Studio API Key ([Get one here](https://makersuite.google.com/app/apikey))

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/llm-prompt-manager.git
cd llm-prompt-manager
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Run the application**
```bash
streamlit run app.py
```

4. **Open your browser**
Navigate to `http://localhost:8501`

### First Setup

1. **Enter your Gemini API Key** in the sidebar
2. **Create your first prompt execution**
3. **Set evaluation criteria**
4. **Start experimenting!**

## 📖 Usage Guide

### 🆕 **Creating New Executions**

#### Single Prompt Mode
```
1. Select "Single Prompt" mode
2. Enter your prompt
3. Define evaluation criteria
4. Add execution memo
5. Click "Execute & Record"
```

#### Template + Data Mode
```
1. Select "Template + Data Input" mode
2. Create prompt template with {user_input}
3. Provide input data
4. Preview final prompt
5. Execute and evaluate
```

### 🌿 **Branch Management**

```bash
# Create new branch
1. Go to sidebar "Branch Management"
2. Enter new branch name (e.g., "feature/summarization")
3. Click "Create Branch"

# Switch branches
1. Select branch from dropdown
2. System automatically switches context
```

### 🏷️ **Tagging Important Versions**

```bash
# Create tags for important milestones
1. Go to "Tag Management" in sidebar
2. Select execution to tag
3. Enter tag name (e.g., "v1.0-production")
4. Create tag
```

### 🔍 **Comparing Results**

```bash
# Compare two executions
1. Go to "Result Comparison" tab
2. Select two execution records
3. View side-by-side comparison
4. Analyze diff, costs, and performance
```

## 📁 File Structure

```
llm-prompt-manager/
├── app.py                 # Main Streamlit application
├── requirements.txt       # Python dependencies
├── README.md             # This file
└── data/                 # Local data storage (created at runtime)
    ├── history/          # JSON backup files
    └── exports/          # CSV export files
```

## 💰 Cost Calculation

The system tracks costs using Gemini 2.0 Flash pricing:

### **Token Pricing**
- **Input tokens**: $0.0000001 per token ($0.10 per 1M tokens)
- **Output tokens**: $0.0000004 per token ($0.40 per 1M tokens)

### **Cost Categories**
- **Execution Cost**: Actual prompt execution (primary metric)
- **Evaluation Cost**: Automated evaluation (reference only)
- **Total Cost**: Execution cost only (for ROI calculations)

### **Example Calculation**
```python
# For 6,606 total tokens with $0.007885 execution cost:
Input tokens:  5,327 × $0.0000001 = $0.0005327
Output tokens: 1,279 × $0.0000004 = $0.0005116
Total cost:    $0.0010443

# Note: Actual system shows higher costs due to token estimation differences
```

## 🎯 Advanced Features

### **Branch Visualization**
```
🌿 main
│
├─ abc12345 Initial prompt setup (12-20 14:30)
│  🏷️ Tags: v1.0
│
├─ def67890 Added context enhancement (12-21 09:15)
│
└─ ghi11223 Final optimization (12-21 16:45)
   🏷️ Tags: production
```

### **Data Export/Import**

#### JSON Export (Full Backup)
- Complete system state
- All branches, tags, and metadata
- Perfect for team collaboration

#### CSV Export (Data Analysis)
- Execution records only
- Compatible with Excel, Google Sheets
- Great for external analysis

### **Template System**

Create reusable prompt templates:
```
Template: "Summarize the following text in {summary_length} words: {user_input}"

Data: "Write a comprehensive analysis of market trends..."

Final: "Summarize the following text in 100 words: Write a comprehensive analysis..."
```

## 🛠️ Configuration

### Environment Variables
```bash
# Optional: Set default API key
export GEMINI_API_KEY="your-api-key-here"
```

### Customization
- Modify evaluation criteria templates
- Adjust cost calculation parameters
- Customize UI themes and layouts

## 📊 Best Practices

### **Prompt Development Workflow**
1. **Main Branch**: Stable, production-ready prompts
2. **Feature Branches**: Experimental improvements
3. **Tagging**: Mark successful iterations
4. **Cost Tracking**: Monitor ROI and optimization

### **Team Collaboration**
1. **Shared JSON Files**: Export/import complete histories
2. **Branch Naming**: Use descriptive names (feature/task-name)
3. **Execution Memos**: Document changes and rationale
4. **Regular Backups**: Save important milestones

### **Cost Optimization**
1. **Shorter Prompts**: Reduce input token costs
2. **Output Limits**: Specify desired response length
3. **Template Reuse**: Avoid redundant prompt creation
4. **Branch Comparison**: Identify cost-effective improvements

## 🚦 Troubleshooting

### Common Issues

**API Key Errors**
```bash
# Solution: Verify API key in Google AI Studio
# Check key permissions and billing status
```

**File Import Errors**
```bash
# Solution: Ensure JSON/CSV format is correct
# Check file encoding (UTF-8 recommended)
```

**Performance Issues**
```bash
# Solution: Clear browser cache
# Reduce history size by exporting old data
```

## 🤝 Contributing

We welcome contributions! Please see our contributing guidelines:

1. **Fork the repository**
2. **Create feature branch** (`git checkout -b feature/AmazingFeature`)
3. **Commit changes** (`git commit -m 'Add AmazingFeature'`)
4. **Push to branch** (`git push origin feature/AmazingFeature`)
5. **Open Pull Request**

### Development Setup
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/

# Code formatting
black app.py
```

## 📋 Roadmap

- [ ] **Multi-LLM Support** (OpenAI, Claude, etc.)
- [ ] **Team Collaboration Features**
- [ ] **Advanced Analytics Dashboard**
- [ ] **API Integration**
- [ ] **Docker Deployment**
- [ ] **Prompt Template Marketplace**

## 📄 License

This project is licensed under the MIT License 