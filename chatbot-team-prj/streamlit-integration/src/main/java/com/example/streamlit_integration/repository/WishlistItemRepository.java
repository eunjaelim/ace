package com.example.streamlit_integration.repository;


import com.example.streamlit_integration.entity.Product;
import com.example.streamlit_integration.entity.WishlistItem;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.security.core.userdetails.User;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface WishlistItemRepository extends JpaRepository<WishlistItem, Long> {
    // Find all wishlist items for a specific user
    List<WishlistItem> findByUser(User user);

    // Check if a product is in a user's wishlist
    boolean existsByUserAndProduct(User user, Product product);

    // Delete a specific product from a user's wishlist
    void deleteByUserAndProduct(User user, Product product);
}