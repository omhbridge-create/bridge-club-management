# Bridge Club Member Management System

A comprehensive Streamlit-based application for managing bridge club members, with dynamic custom fields, Excel import/export, and cloud database integration.

## Features

- **Member Management**: Add, edit, and delete club members with multiple categories (Members, Athletes, Students, Interested)
- **Dynamic Custom Fields**: Create custom fields (e.g., ΑΜΚΑ) that can be applied to specific member categories
- **Advanced Filtering**: Filter members by status, year, name, email, and custom fields
- **Excel Import/Export**: 
  - Import member data from Excel files with custom field mapping
  - Export filtered or all data to Excel with timestamps
- **Cloud Database**: PostgreSQL via Supabase for multi-user access and reliability
- **Greek Language Interface**: Full support for Greek language interface

## Technology Stack

- **Frontend**: Streamlit
- **Database**: PostgreSQL (Supabase)
- **Data Processing**: Pandas
- **Export**: OpenPyXL

## Getting Started

### Prerequisites

- Python 3.8+
- Supabase account (free tier available)
- Streamlit account (for deployment)

### Installation

1. Clone the repository:
\`\`\`bash
git clone https://github.com/yourusername/bridge-club-management.git
cd bridge-club-management
\`\`\`

2. Install dependencies:
\`\`\`bash
pip install -r requirements.txt
\`\`\`

3. Set environment variables:
\`\`\`bash
export POSTGRES_URL="your_postgres_url"
export SUPABASE_URL="your_supabase_url"
\`\`\`

### Running Locally

\`\`\`bash
streamlit run clubappv01.py
\`\`\`

Visit `http://localhost:8501` in your browser.

## Usage

### Tab 1: Add New Member
- Fill in general information, then select member category expanders
- Add custom field values for applicable categories
- Save to add the member to the database

### Tab 2-5: View Members by Category
- Browse members in each category with their details
- View associated custom field values

### Tab 6: All Members
- View all members in one place
- Apply advanced filters by status, dates, names, or emails
- Export filtered or all data to Excel

### Tab 7: Settings
- Change club name

### Tab 8: Import Data
- Upload Excel files with member data
- Map Excel columns to database fields
- Import custom field data

### Tab 9: Custom Fields Management
- Create new custom fields (e.g., ΑΜΚΑ, ID numbers)
- Specify which member categories each field applies to
- Delete custom fields when no longer needed

## Database Schema

### people
Main member table with personal and category information

### custom_fields
Definitions of custom fields and which categories they apply to

### member_attributes
Values for custom fields per member

### settings
Application settings (currently club name)

## Deployment

### Deploy to Streamlit Cloud

1. Push your repository to GitHub
2. Visit [share.streamlit.io](https://share.streamlit.io)
3. Create a new app and connect your GitHub repository
4. Add environment variables:
   - `POSTGRES_URL`: Your Supabase PostgreSQL connection string
   - `SUPABASE_URL`: Your Supabase project URL
5. Deploy!

## Contributing

Contributions are welcome. Please create a fork and submit a pull request.

## License

MIT License

## Support

For issues or questions, please open an issue on GitHub.
