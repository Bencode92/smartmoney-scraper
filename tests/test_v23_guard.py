"""Tests Guard v2.3 — Vérifie l'isolation v2.2/v2.3

Ce fichier contient des tests qui garantissent que:
1. v2.3 hérite de SmartMoneyEngineBase (pas de v2.2)
2. v2.3 n'utilise pas implicitement le scoring v2.2
3. Les méthodes critiques sont bien surchargées

Exécution:
    pytest tests/test_v23_guard.py -v
"""

import pytest
import inspect


class TestV23Inheritance:
    """Tests d'isolation d'héritage v2.3."""
    
    def test_v23_inherits_from_base_not_v22(self):
        """v2.3 doit hériter de SmartMoneyEngineBase, PAS de SmartMoneyEngine/V22."""
        from src.engine_v23 import SmartMoneyEngineV23
        from src.engine_base import SmartMoneyEngineBase
        
        # Vérifier que v2.3 hérite de Base
        assert issubclass(SmartMoneyEngineV23, SmartMoneyEngineBase), \
            "SmartMoneyEngineV23 DOIT hériter de SmartMoneyEngineBase"
        
        # Vérifier les parents directs (Method Resolution Order)
        mro = SmartMoneyEngineV23.__mro__
        parent_names = [cls.__name__ for cls in mro]
        
        # SmartMoneyEngineBase doit être dans la chaîne
        assert "SmartMoneyEngineBase" in parent_names, \
            f"SmartMoneyEngineBase non trouvé dans MRO: {parent_names}"
        
        # SmartMoneyEngine (ancien) et SmartMoneyEngineV22 ne doivent PAS être dans la chaîne
        forbidden_parents = ["SmartMoneyEngine", "SmartMoneyEngineV22"]
        for forbidden in forbidden_parents:
            if forbidden in parent_names:
                pytest.fail(
                    f"ERREUR: {forbidden} trouvé dans l'héritage de V23!\n"
                    f"MRO: {parent_names}\n"
                    f"V2.3 doit hériter UNIQUEMENT de SmartMoneyEngineBase."
                )
    
    def test_v22_inherits_from_base_not_engine(self):
        """v2.2 doit aussi hériter de SmartMoneyEngineBase."""
        from src.engine_v22 import SmartMoneyEngineV22
        from src.engine_base import SmartMoneyEngineBase
        
        assert issubclass(SmartMoneyEngineV22, SmartMoneyEngineBase), \
            "SmartMoneyEngineV22 DOIT hériter de SmartMoneyEngineBase"
    
    def test_v23_has_own_scoring_methods(self):
        """v2.3 doit avoir ses propres méthodes de scoring (pas héritées de v2.2)."""
        from src.engine_v23 import SmartMoneyEngineV23
        
        # Ces méthodes doivent être définies dans v2.3 (pas juste héritées)
        required_methods = [
            "score_smart_money",
            "score_insider", 
            "score_momentum",
            "_prepare_ranks",
            "calculate_scores_v23",
            "apply_filters_v23",
        ]
        
        for method_name in required_methods:
            method = getattr(SmartMoneyEngineV23, method_name, None)
            assert method is not None, f"Méthode {method_name} manquante dans V23"
            
            # Vérifier que la méthode est définie dans V23 (pas héritée de Base)
            if method_name not in ["calculate_scores", "apply_filters"]:
                defining_class = None
                for cls in SmartMoneyEngineV23.__mro__:
                    if method_name in cls.__dict__:
                        defining_class = cls.__name__
                        break
                
                assert defining_class == "SmartMoneyEngineV23", \
                    f"{method_name} défini dans {defining_class}, devrait être dans SmartMoneyEngineV23"
    
    def test_v23_implements_abstract_methods(self):
        """v2.3 doit implémenter les méthodes abstraites de Base."""
        from src.engine_v23 import SmartMoneyEngineV23
        
        # Ces méthodes sont abstraites dans Base et doivent être implémentées
        abstract_methods = ["calculate_scores", "apply_filters"]
        
        for method_name in abstract_methods:
            method = getattr(SmartMoneyEngineV23, method_name, None)
            assert method is not None, f"Méthode abstraite {method_name} non implémentée"
            
            # Vérifier que c'est bien une méthode (pas une référence abstraite)
            assert callable(method), f"{method_name} n'est pas callable"


class TestV23ScoringIsolation:
    """Tests d'isolation du scoring v2.3."""
    
    def test_v23_weights_differ_from_v22(self):
        """Les poids v2.3 doivent être différents de v2.2."""
        from src.engine_v22 import SmartMoneyEngineV22
        from src.engine_v23 import SmartMoneyEngineV23
        
        v22 = SmartMoneyEngineV22()
        v23 = SmartMoneyEngineV23()
        
        # smart_money doit être réduit dans v2.3
        assert v23.weights.get("smart_money", 1.0) < v22.weights.get("smart_money", 0), \
            f"smart_money v2.3 ({v23.weights.get('smart_money')}) devrait être < v2.2 ({v22.weights.get('smart_money')})"
        
        # v2.3 doit avoir value, quality, risk
        assert "value" in v23.weights, "v2.3 doit avoir un poids 'value'"
        assert "quality" in v23.weights, "v2.3 doit avoir un poids 'quality'"
        assert "risk" in v23.weights, "v2.3 doit avoir un poids 'risk'"
        
        # v2.2 ne devrait PAS avoir ces poids
        assert "value" not in v22.weights, "v2.2 ne devrait pas avoir 'value'"
    
    def test_v23_version_string(self):
        """v2.3 doit avoir la bonne version."""
        from src.engine_v23 import SmartMoneyEngineV23
        
        engine = SmartMoneyEngineV23()
        assert engine.version == "2.3", f"Version incorrecte: {engine.version}"
    
    def test_v22_version_string(self):
        """v2.2 doit avoir la bonne version."""
        from src.engine_v22 import SmartMoneyEngineV22
        
        engine = SmartMoneyEngineV22()
        assert engine.version == "2.2", f"Version incorrecte: {engine.version}"


class TestArchitectureIntegrity:
    """Tests d'intégrité de l'architecture."""
    
    def test_base_is_abstract(self):
        """SmartMoneyEngineBase doit être une classe abstraite."""
        from src.engine_base import SmartMoneyEngineBase
        from abc import ABC
        
        assert issubclass(SmartMoneyEngineBase, ABC), \
            "SmartMoneyEngineBase doit hériter de ABC"
    
    def test_base_has_abstract_methods(self):
        """SmartMoneyEngineBase doit déclarer des méthodes abstraites."""
        from src.engine_base import SmartMoneyEngineBase
        import abc
        
        # Récupérer les méthodes abstraites
        abstract_methods = set()
        for name, method in inspect.getmembers(SmartMoneyEngineBase):
            if getattr(method, "__isabstractmethod__", False):
                abstract_methods.add(name)
        
        expected_abstract = {"calculate_scores", "apply_filters"}
        assert expected_abstract.issubset(abstract_methods), \
            f"Méthodes abstraites attendues: {expected_abstract}, trouvées: {abstract_methods}"
    
    def test_both_engines_can_instantiate(self):
        """Les deux engines doivent pouvoir être instanciés."""
        from src.engine_v22 import SmartMoneyEngineV22
        from src.engine_v23 import SmartMoneyEngineV23
        
        # V22
        try:
            v22 = SmartMoneyEngineV22()
            assert v22 is not None
        except Exception as e:
            pytest.fail(f"Impossible d'instancier V22: {e}")
        
        # V23
        try:
            v23 = SmartMoneyEngineV23()
            assert v23 is not None
        except Exception as e:
            pytest.fail(f"Impossible d'instancier V23: {e}")
    
    def test_shared_methods_in_base(self):
        """Les méthodes communes doivent être dans Base."""
        from src.engine_base import SmartMoneyEngineBase
        
        # Ces méthodes doivent être dans Base (partagées par v2.2 et v2.3)
        shared_methods = [
            "load_data",
            "enrich",
            "clean_universe",
            "optimize",
            "export",
        ]
        
        for method_name in shared_methods:
            method = getattr(SmartMoneyEngineBase, method_name, None)
            assert method is not None, \
                f"Méthode partagée {method_name} manquante dans SmartMoneyEngineBase"


# === SMOKE TEST ===

class TestV23Smoke:
    """Smoke test rapide pour v2.3."""
    
    def test_v23_pipeline_smoke(self):
        """Test que le pipeline v2.3 peut démarrer sans erreur d'import."""
        from src.engine_v23 import SmartMoneyEngineV23
        
        engine = SmartMoneyEngineV23()
        
        # Vérifier les attributs essentiels
        assert hasattr(engine, "universe")
        assert hasattr(engine, "portfolio")
        assert hasattr(engine, "weights")
        assert hasattr(engine, "constraints")
        assert hasattr(engine, "version")
        
        # Vérifier les méthodes essentielles
        assert callable(getattr(engine, "load_data", None))
        assert callable(getattr(engine, "enrich", None))
        assert callable(getattr(engine, "apply_filters_v23", None))
        assert callable(getattr(engine, "calculate_scores_v23", None))
        assert callable(getattr(engine, "optimize", None))
        assert callable(getattr(engine, "export", None))
        assert callable(getattr(engine, "get_top_buffett", None))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
