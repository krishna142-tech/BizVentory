# BizVentory - Smart Inventory Management System

BizVentory is a modern, web-based inventory management system designed to help small and medium-sized businesses streamline their inventory operations.

## Features

- **Smart Dashboard**: Real-time overview of inventory status and critical metrics
- **Inventory Management**: Automated stock tracking and categorization
- **Shopping Interface**: User-friendly product catalog with advanced filtering
- **Business Intelligence**: AI-powered inventory predictions and analytics
- **Transaction Management**: Detailed history and automated record-keeping
- **Security**: Secure user authentication and data protection

## Known Issues

⚠️ **Report Downloads**: There are currently issues with downloading reports. This is a known issue that will be fixed as soon as possible. We apologize for any inconvenience this may cause.

## Tech Stack

- **Backend**: Python Flask
- **Database**: MongoDB
- **Frontend**: HTML5, CSS3, JavaScript
- **Authentication**: Flask-Login
- **Security**: CSRF Protection

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/BizVentory.git
cd BizVentory
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the root directory:
```env
SECRET_KEY=your-super-secret-key-change-this-in-production
MONGO_URI=mongodb://localhost:27017/bizventory_main
```

5. Run the application:
```bash
python app.py
```

## Usage

1. Register a new account
2. Set up your business profile
3. Add inventory items
4. Start managing your inventory

## Contributing

1. Fork the repository
2. Create a new branch (`git checkout -b feature/improvement`)
3. Make changes and commit (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature/improvement`)
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

- Email: your.email@example.com
- GitHub: [@yourusername](https://github.com/yourusername)

## Acknowledgments

- Flask framework
- MongoDB
- Font Awesome icons 