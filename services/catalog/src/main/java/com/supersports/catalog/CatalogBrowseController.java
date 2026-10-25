package com.supersports.catalog;

import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.dao.EmptyResultDataAccessException;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/api/v1/catalog/public/products")
class CatalogBrowseController {
    private final CatalogRepository repository;
    CatalogBrowseController(CatalogRepository repository) { this.repository=repository; }

    @GetMapping Map<String,Object> browse(@RequestParam(defaultValue="1") int page,
            @RequestParam(defaultValue="24") int pageSize, @RequestParam(required=false) String q,
            @RequestParam(required=false) String category, @RequestParam(required=false) String sport) {
        if(page<1 || page>10000 || pageSize<1 || pageSize>48) throw bad("page must be 1..10000 and pageSize 1..48");
        return repository.browse(page,pageSize,filter(q,100),filter(category,64),filter(sport,64));
    }
    @GetMapping("/{slug}") Map<String,Object> detail(@PathVariable String slug) {
        try { return repository.productBySlug(slug(slug)); }
        catch(EmptyResultDataAccessException e) { throw missing(); }
    }
    @GetMapping("/by-skus") List<Map<String,Object>> bySkus(@RequestParam List<UUID> skuIds) {
        if(skuIds.isEmpty() || skuIds.size()>100 || skuIds.stream().distinct().count()!=skuIds.size())
            throw bad("Supply 1 to 100 unique SKU IDs");
        return repository.productsForSkus(skuIds);
    }
    @GetMapping("/{slug}/similar") List<Map<String,Object>> similar(@PathVariable String slug,@RequestParam(defaultValue="8") int limit) {
        if(limit<1 || limit>12) throw bad("limit must be 1..12");
        try { return repository.similar(slug(slug),limit); }
        catch(EmptyResultDataAccessException e) { throw missing(); }
    }
    private static String slug(String value) {
        if(!value.matches("[a-zA-Z0-9_-]{1,100}")) throw bad("Invalid product slug");
        return value;
    }
    private static String filter(String value,int max) {
        if(value!=null && value.length()>max) throw bad("Filter exceeds "+max+" characters");
        return value==null || value.isBlank() ? null : value.trim();
    }
    private static ResponseStatusException bad(String message) { return new ResponseStatusException(HttpStatus.BAD_REQUEST,message); }
    private static ResponseStatusException missing() { return new ResponseStatusException(HttpStatus.NOT_FOUND,"Active product not found"); }
}
