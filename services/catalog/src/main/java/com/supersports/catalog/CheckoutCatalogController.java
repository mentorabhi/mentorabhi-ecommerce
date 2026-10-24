package com.supersports.catalog;
import java.util.Map;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@RestController @RequestMapping("/api/v1/internal/checkout/catalog")
class CheckoutCatalogController {
    private final CatalogRepository repository;
    CheckoutCatalogController(CatalogRepository repository){this.repository=repository;}
    @GetMapping("/skus/{skuId}") Map<String,Object> sku(@PathVariable UUID skuId){
        try{return repository.checkoutSku(skuId);}
        catch(org.springframework.dao.EmptyResultDataAccessException e){throw new ResponseStatusException(HttpStatus.NOT_FOUND,"SKU not found");}
    }
}
