package com.example.streamlit_integration.controller;


import com.example.streamlit_integration.dto.UserDto;
import com.example.streamlit_integration.dto.WishlistRequest;
import com.example.streamlit_integration.entity.Product;
import com.example.streamlit_integration.entity.User;
import com.example.streamlit_integration.entity.WishlistItem;
import com.example.streamlit_integration.repository.UserRepository;
import com.example.streamlit_integration.service.UserService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import javax.transaction.Transactional;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.stream.Collectors;
@CrossOrigin(origins = "http://localhost:8501")
@RestController
@RequestMapping("/user")
public class UserController {

    @Autowired
    UserRepository userRepository;
    @Autowired
    private UserService userService;

    // 사용자 정보 업데이트 API
    // 사용자 정보 업데이트 API
    public boolean updateUser(UserDto userDto) {
        Optional<User> userOptional = userRepository.findByUsername(userDto.getUsername());

        if (userOptional.isPresent()) {
            User user = userOptional.get();

            // Only update fields that are non-null
            if (userDto.getEmail() != null) {
                user.setEmail(userDto.getEmail());
            }
            if (userDto.getPhoneNumber() != null) {
                user.setPhoneNumber(userDto.getPhoneNumber());
            }

            // Save the updated user back to the database
            userRepository.save(user);
            return true;
        } else {
            System.out.println("User not found: " + userDto.getUsername());
            return false;
        }
    }

    // 사용자 정보 조회 API (username으로 조회)
    @GetMapping("/{username}")
    public ResponseEntity<Map<String, Object>> getUserByUsername(@PathVariable String username) {
        Optional<User> userOptional = userService.findUserByUsername(username);
        if (userOptional.isPresent()) {
            User user = userOptional.get();
            Map<String, Object> userInfo = new HashMap<>();
            userInfo.put("username", user.getUsername());
            userInfo.put("email", user.getEmail());
            userInfo.put("phone_number", user.getPhoneNumber());
            userInfo.put("wishlist", user.getWishlist());

            // Content-Type 명시적으로 설정
            return ResponseEntity
                    .ok()
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(userInfo);
        } else {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).body(null);
        }
    }

    // 찜 리스트 저장 API
    @PostMapping("/wishlist")
    public ResponseEntity<String> saveWishlist(@RequestBody WishlistRequest request) {
        String username = request.getUsername();
        List<Product> wishlist = request.getWishlist();

        // 찜한 상품 처리 로직

        return ResponseEntity.ok("찜 리스트 저장 성공");
    }

    // 유저의 찜 리스트 불러오기 API
    @GetMapping("user/{username}/wishlist")
    public ResponseEntity<List<Product>> getWishlist(@PathVariable String username) {
        List<WishlistItem> wishlistItems = userService.getWishlist(username);  // WishlistItem 리스트를 가져옴
        if (wishlistItems != null) {
            // WishlistItem에서 Product만 추출하여 List<Product>로 변환
            List<Product> products = wishlistItems.stream()
                    .map(WishlistItem::getProduct)  // WishlistItem에서 Product를 추출
                    .collect(Collectors.toList());

            return ResponseEntity.ok(products);
        } else {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).body(null);
        }
    }

    // 찜한 리스트 전체 삭제 API
    @Transactional  // 트랜잭션으로 묶어 데이터의 일관성을 유지
    @DeleteMapping("user/{username}/wishlist/delete")
    public ResponseEntity<String> deleteAllWishlist(@PathVariable String username) {
        try {
            boolean success = userService.deleteAllWishlistItems(username);
            if (success) {
                return ResponseEntity.ok("찜 리스트가 성공적으로 삭제되었습니다.");
            } else {
                return ResponseEntity.status(HttpStatus.NOT_FOUND).body("해당 사용자의 찜 리스트를 찾을 수 없습니다.");
            }
        } catch (Exception e) {
            // 예외 처리 및 로그 출력
            System.err.println("Error deleting wishlist: " + e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body("찜 리스트 삭제 중 오류 발생");
        }
    }

    // 사용자 정보 부분 업데이트 API (PATCH)

    @Transactional  // 트랜잭션 어노테이션 추가
    @PutMapping("/{username}/update")
    public ResponseEntity<String> updateUserPartial(@PathVariable String username, @RequestBody UserDto userDto) {
        // 입력된 데이터 로그
        System.out.println("Received request to update user: " + username);
        System.out.println("Data received -> email: " + userDto.getEmail() + ", phone: " + userDto.getPhoneNumber());

        try {
            // userService 호출 전에 디버깅 로그 추가
            System.out.println("Calling userService.updateUser with data: " + userDto.toString());

            boolean isUpdated = userService.updateUser(userDto);

            // userService 메서드 결과 로그
            if (isUpdated) {
                System.out.println("User update successful for user: " + username);
                return ResponseEntity.ok("User partially updated successfully");
            } else {
                System.out.println("User update failed for user: " + username);
                return ResponseEntity.status(HttpStatus.BAD_REQUEST).body("Failed to update user partially");
            }
        } catch (Exception e) {
            // 예외가 발생한 경우 로그에 에러 출력
            System.err.println("Error while updating user: " + e.getMessage());
            e.printStackTrace();
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body("Error occurred while updating user");
        }
    }





}
