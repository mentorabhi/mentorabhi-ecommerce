package com.supersports.inventory;

import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/api/v1/internal/checkout/inventory/returns")
class CheckoutInventoryReturnController {
    private final InventoryRepository repository;
    CheckoutInventoryReturnController(InventoryRepository repository){this.repository=repository;}

    @PostMapping("/{returnId}/receive") Map<String,Object> receive(@PathVariable UUID returnId,@RequestBody Manifest request){
        if(request==null||request.orderId()==null||request.units()==null||request.units().stream().anyMatch(java.util.Objects::isNull))throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY,"Invalid return manifest");
        try{return repository.registerReturn(returnId,request.orderId(),request.units()==null?null:request.units().stream().map(unit->new ReturnInspectionRules.UnitKey(unit.skuId(),unit.ordinal())).toList());}
        catch(InventoryRepository.ReturnOperationConflictException conflict){throw new ResponseStatusException(HttpStatus.CONFLICT,"Return manifest conflicts with an existing receipt");}
        catch(IllegalArgumentException invalid){throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY,"Invalid return manifest");}
    }
    record Manifest(UUID orderId,List<Unit> units){}
    record Unit(UUID skuId,int ordinal){}
}
