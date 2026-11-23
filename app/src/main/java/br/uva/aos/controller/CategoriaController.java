package br.uva.aos.controller;

import br.uva.aos.dto.CategoriaDTO;
import br.uva.aos.service.CacheInstrumentado;
import br.uva.aos.service.CategoriaService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/categorias")
public class CategoriaController {

    private final CategoriaService service;
    private final CacheInstrumentado cacheInstrumentado;

    public CategoriaController(CategoriaService service, CacheInstrumentado cacheInstrumentado) {
        this.service = service;
        this.cacheInstrumentado = cacheInstrumentado;
    }

    @GetMapping("/sem-cache")
    public List<CategoriaDTO> semCache() {
        return service.listarSemCache();
    }

    @GetMapping("/com-cache")
    public List<CategoriaDTO> comCache() {
        return cacheInstrumentado.categoriasComCache();
    }
}
