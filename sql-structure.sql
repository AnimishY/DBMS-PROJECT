-- Moved to the 'sql' folder for better organization.

-- 1. Buyer Table (with fragmented personal address)
CREATE TABLE Buyer (
    BuyerId INT AUTO_INCREMENT PRIMARY KEY,
    BuyerFirstName VARCHAR(50) NOT NULL,
    BuyerLastName VARCHAR(50) NOT NULL,
    AddressLine1 VARCHAR(100) NOT NULL,
    AddressLine2 VARCHAR(100) NULL,
    City VARCHAR(50) NOT NULL,
    States VARCHAR(50) NOT NULL,
    PinCode VARCHAR(20) NOT NULL,
    Email VARCHAR(100) NOT NULL UNIQUE,
    PasswordHash VARCHAR(16) NOT NULL
);

-- 2. Seller Table (with fragmented store address and store name)
CREATE TABLE Seller (
    SellerId INT AUTO_INCREMENT PRIMARY KEY,
    StoreName VARCHAR(100) NOT NULL,
    SellerContact VARCHAR(100) NOT NULL,
    StoreAddressLine1 VARCHAR(100) NOT NULL,
    StoreAddressLine2 VARCHAR(100) NULL,
    City VARCHAR(50) NOT NULL,
    States VARCHAR(50) NOT NULL,
    PinCode VARCHAR(20) NOT NULL,
    Email VARCHAR(100) NOT NULL UNIQUE,
    PasswordHash VARCHAR(16) NOT NULL
);

-- 3. Category Table
CREATE TABLE Category (
    CategoryId INT AUTO_INCREMENT PRIMARY KEY,
    Name VARCHAR(100) NOT NULL,
    Description TEXT NULL
);

-- 4. Product Table (includes SellerId and CategoryId)
CREATE TABLE Product (
    ProductId INT AUTO_INCREMENT PRIMARY KEY,
    CategoryId INT NOT NULL,
    SellerId INT NOT NULL,
    Name VARCHAR(100) NOT NULL,
    Description TEXT NULL,
    Price DECIMAL(10,2) NOT NULL,
    Stock INT NOT NULL,
    image_path VARCHAR(255),  -- New column for image path
    CreatedAt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (CategoryId) REFERENCES Category(CategoryId) ON DELETE NO ACTION,
    FOREIGN KEY (SellerId) REFERENCES Seller(SellerId) ON DELETE NO ACTION
    -- there a property for product image as well which gives a path which is in statics/uploads
);

-- 5. Orders Table
CREATE TABLE Orders (
    OrderId INT AUTO_INCREMENT PRIMARY KEY,
    BuyerId INT NOT NULL,
    OrderDate DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    TotalAmount DECIMAL(10,2) NOT NULL,
    OrderStatus VARCHAR(50) NOT NULL,
    FOREIGN KEY (BuyerId) REFERENCES Buyer(BuyerId) ON DELETE CASCADE
);

-- 6. OrderItem Table
CREATE TABLE OrderItem (
    OrderItemId INT AUTO_INCREMENT PRIMARY KEY,
    OrderId INT NOT NULL,
    ProductId INT NOT NULL,
    Quantity INT NOT NULL,
    UnitPrice DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (OrderId) REFERENCES Orders(OrderId) ON DELETE CASCADE,
    FOREIGN KEY (ProductId) REFERENCES Product(ProductId) ON DELETE CASCADE
);

-- 7. Payment Table
CREATE TABLE Payment (
    PaymentId INT AUTO_INCREMENT PRIMARY KEY,
    OrderId INT NOT NULL,
    PaymentDate DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PaymentMethod VARCHAR(50) NOT NULL,
    Amount DECIMAL(10,2) NOT NULL,
    PaymentStatus VARCHAR(50) NOT NULL,
    FOREIGN KEY (OrderId) REFERENCES Orders(OrderId) ON DELETE CASCADE
);

-- 8. Shipment Table
CREATE TABLE Shipment (
    ShipmentId INT AUTO_INCREMENT PRIMARY KEY,
    OrderId INT NOT NULL,
    ShipmentDate DATETIME NULL,
    DeliveryDate DATETIME NULL,
    ShippingMethod VARCHAR(50) NULL,
    TrackingNumber VARCHAR(100) NULL,
    FOREIGN KEY (OrderId) REFERENCES Orders(OrderId) ON DELETE CASCADE
);

-- 9. Review Table
CREATE TABLE Review (
    ReviewId INT AUTO_INCREMENT PRIMARY KEY,
    BuyerId INT NOT NULL,
    ProductId INT NOT NULL,
    Rating TINYINT NOT NULL CHECK (Rating BETWEEN 1 AND 5),
    Comment TEXT NULL,
    ReviewDate DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (BuyerId) REFERENCES Buyer(BuyerId) ON DELETE CASCADE,
    FOREIGN KEY (ProductId) REFERENCES Product(ProductId) ON DELETE CASCADE,
    UNIQUE (BuyerId, ProductId)
);

-- 10. Cart Table (each buyer owns one cart)
CREATE TABLE Cart (
    CartId INT AUTO_INCREMENT PRIMARY KEY,
    BuyerId INT NOT NULL UNIQUE,
    CreatedAt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (BuyerId) REFERENCES Buyer(BuyerId) ON DELETE CASCADE
);

-- 11. CartItem Table (items added to a cart)
CREATE TABLE CartItem (
    CartItemId INT AUTO_INCREMENT PRIMARY KEY,
    CartId INT NOT NULL,
    ProductId INT NOT NULL,
    Quantity INT NOT NULL,
    AddedAt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (CartId) REFERENCES Cart(CartId) ON DELETE CASCADE,
    FOREIGN KEY (ProductId) REFERENCES Product(ProductId) ON DELETE CASCADE,
    UNIQUE (CartId, ProductId)
);
