"""
Tests for Transformer Module
----------------------------
Valida las reglas de negocio de transformación.
"""

import pytest
from transformer import (
    resolve_entity_conflicts,
    deduplicate_resources,
    calculate_repetitions
)
import pandas as pd


class TestResolveEntityConflicts:
    """Tests para resolución de conflictos entidad/excepción."""
    
    def test_filters_matching_exceptions(self):
        """Debe filtrar registros que tienen excepción en la misma fecha."""
        attendance = {
            ('2025-01-01', 'Entity_A'),
            ('2025-01-02', 'Entity_A'),
            ('2025-01-01', 'Entity_B')
        }
        exceptions = {
            ('Entity_A', '2025-01-01')  # Entity_A tiene excepción el 01
        }
        
        result = resolve_entity_conflicts(attendance, exceptions)
        
        assert ('2025-01-01', 'Entity_A') not in result
        assert ('2025-01-02', 'Entity_A') in result
        assert ('2025-01-01', 'Entity_B') in result
    
    def test_returns_all_if_no_exceptions(self):
        """Si no hay excepciones, retorna todos los registros."""
        attendance = {('2025-01-01', 'Entity_A')}
        exceptions = set()
        
        result = resolve_entity_conflicts(attendance, exceptions)
        
        assert len(result) == 1


class TestDeduplicateResources:
    """Tests para deduplicación de recursos."""
    
    def test_removes_duplicates_same_session(self):
        """Debe eliminar recursos duplicados en la misma sesión."""
        df = pd.DataFrame([
            {'Fecha_Clean': '2025-01-01', 'Grupo_Clean': 'A', 'Resource': 'R1'},
            {'Fecha_Clean': '2025-01-01', 'Grupo_Clean': 'A', 'Resource': 'R1'},  # Duplicado
            {'Fecha_Clean': '2025-01-01', 'Grupo_Clean': 'A', 'Resource': 'R2'}
        ])
        
        result = deduplicate_resources(df)
        
        assert len(result) == 2
    
    def test_keeps_same_resource_different_groups(self):
        """Permite el mismo recurso en diferentes grupos."""
        df = pd.DataFrame([
            {'Fecha_Clean': '2025-01-01', 'Grupo_Clean': 'A', 'Resource': 'R1'},
            {'Fecha_Clean': '2025-01-01', 'Grupo_Clean': 'B', 'Resource': 'R1'}
        ])
        
        result = deduplicate_resources(df)
        
        assert len(result) == 2


class TestCalculateRepetitions:
    """Tests para cálculo de repeticiones."""
    
    def test_counts_repetitions_correctly(self):
        """Debe contar correctamente las repeticiones."""
        df = pd.DataFrame([
            {'Entity': 'E1', 'Resource': 'R1', 'Fecha': '2025-01-01'},
            {'Entity': 'E1', 'Resource': 'R1', 'Fecha': '2025-01-02'},
            {'Entity': 'E1', 'Resource': 'R1', 'Fecha': '2025-01-03'},
            {'Entity': 'E2', 'Resource': 'R1', 'Fecha': '2025-01-01'}
        ])
        
        result = calculate_repetitions(df)
        
        e1_r1 = result[(result['Entity'] == 'E1') & (result['Resource'] == 'R1')]
        assert e1_r1['Count'].values[0] == 3


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
