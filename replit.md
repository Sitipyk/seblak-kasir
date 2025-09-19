# Seblak Kasir System

## Overview
A complete cashier system for a Seblak (Indonesian spicy snack) business, built with Streamlit. The application manages transactions, inventory, sales reports, and statistics for a Seblak restaurant.

## Project Architecture
- **Technology**: Python + Streamlit
- **Main Application**: `app.py` - The complete Streamlit application
- **Frontend**: Static HTML template in `index.html` (reference design)
- **Port**: 5000 (configured for Replit environment)
- **Deployment**: Configured for autoscale deployment target

## Features
- **Kasir (Cashier)**: Process transactions with menu selection and toppings
- **Stok (Inventory)**: Manage product stock levels
- **Laporan Penjualan (Sales Reports)**: View sales data by month
- **Statistik (Statistics)**: Analyze best-selling products
- **Pengaturan (Settings)**: Add/remove products

## Recent Changes
- 2025-09-19: Initial setup for Replit environment
  - Installed Python 3.11 and required packages (streamlit, pandas, numpy, matplotlib)
  - Configured Streamlit workflow to run on 0.0.0.0:5000
  - Set up deployment configuration for autoscale
  - Verified application functionality

## Configuration
- **Workflow**: Streamlit Server running on port 5000
- **Command**: `streamlit run app.py --server.address=0.0.0.0 --server.port=5000 --server.headless=true`
- **Deployment**: Autoscale configuration for production deployment

## Notes
- Application uses session state to maintain data (no persistent database)
- Some deprecation warnings present in Streamlit (use_container_width parameter)
- Ready for production deployment through Replit