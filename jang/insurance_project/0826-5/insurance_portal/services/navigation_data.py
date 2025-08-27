# -*- coding: utf-8 -*-
# insurance_portal/services/navigation_data.py
# 목적: 교통사고 과실비율 네비게이션 트리 데이터 관리

import logging

logger = logging.getLogger(__name__)

class NavigationDataManager:
    """
    교통사고 과실비율 네비게이션 데이터를 관리하는 클래스
    """
    
    def __init__(self):
        self.navigation_tree = self._build_navigation_tree()
        self.current_path = []
        
    def _build_navigation_tree(self):
        """
        예시 네비게이션 트리 구조 (실제 데이터는 나중에 결정)
        """
        return {
            "교차로 사고": {
                "icon": "fas fa-traffic-light",
                "description": "교차로에서 발생한 사고",
                "children": {
                    "신호등 교차로": {
                        "icon": "fas fa-traffic-light", 
                        "description": "신호등이 있는 교차로",
                        "children": {
                            "직진 vs 좌회전": {
                                "icon": "fas fa-arrows-alt-h",
                                "description": "직진 차량과 좌회전 차량 간 사고",
                                "options": [
                                    "직진차 신호준수 - 좌회전차 신호준수",
                                    "직진차 신호준수 - 좌회전차 신호위반",
                                    "직진차 신호위반 - 좌회전차 신호준수"
                                ]
                            }
                        }
                    }
                }
            },
            "추돌 사고": {
                "icon": "fas fa-car-crash",
                "description": "앞차를 뒤에서 추돌한 사고",
                "children": {
                    "일반 추돌": {
                        "icon": "fas fa-car-side",
                        "description": "일반적인 추돌 상황",
                        "children": {
                            "신호대기 중": {
                                "icon": "fas fa-pause-circle",
                                "description": "신호대기 중 추돌",
                                "options": [
                                    "정상 신호대기 중 - 후방 추돌",
                                    "급정거 - 후방 추돌",
                                    "신호위반 정지 - 후방 추돌"
                                ]
                            }
                        }
                    }
                }
            },
            "차로변경 사고": {
                "icon": "fas fa-car-side",
                "description": "차로를 변경하면서 발생한 사고",
                "children": {
                    "일반도로": {
                        "icon": "fas fa-road",
                        "description": "일반도로에서의 차로변경",
                        "children": {
                            "급진입": {
                                "icon": "fas fa-sign-in-alt",
                                "description": "급작스런 차로 진입",
                                "options": [
                                    "급작스런 차로변경",
                                    "안전거리 미확보",
                                    "방향지시등 미점등"
                                ]
                            }
                        }
                    }
                }
            }
        }
    
    def get_navigation_data(self, path=None):
        """
        현재 경로에 해당하는 네비게이션 데이터 반환
        
        Args:
            path (list): 네비게이션 경로 [level1, level2, level3]
            
        Returns:
            dict: 현재 레벨의 네비게이션 데이터
        """
        if not path:
            # 최상위 레벨 반환
            return {
                "level": 0,
                "title": "교통사고 유형을 선택해주세요",
                "items": [
                    {
                        "key": key,
                        "title": key,
                        "icon": value["icon"],
                        "description": value["description"]
                    }
                    for key, value in self.navigation_tree.items()
                ]
            }
        
        try:
            current_node = self.navigation_tree
            level = 0
            
            # 경로를 따라 이동
            for step in path:
                if step not in current_node:
                    raise KeyError(f"Invalid path: {step}")
                current_node = current_node[step]
                level += 1
            
            # 현재 노드가 children을 가지고 있는지 확인
            if "children" in current_node:
                return {
                    "level": level,
                    "path": path,
                    "title": f"{' > '.join(path)} 세부 유형을 선택해주세요",
                    "items": [
                        {
                            "key": key,
                            "title": key,
                            "icon": value["icon"],
                            "description": value["description"]
                        }
                        for key, value in current_node["children"].items()
                    ]
                }
            
            # 최종 선택 옵션인 경우
            elif "options" in current_node:
                return {
                    "level": level,
                    "path": path,
                    "title": f"{' > '.join(path)} 상세 상황을 선택해주세요",
                    "is_final": True,
                    "icon": current_node["icon"],
                    "description": current_node["description"],
                    "options": current_node["options"]
                }
            
            else:
                raise ValueError("Invalid node structure")
                
        except (KeyError, ValueError) as e:
            logger.error(f"Navigation error: {e}")
            return self.get_navigation_data()  # 최상위로 돌아감
    
    def build_breadcrumb(self, path):
        """
        현재 경로를 기반으로 breadcrumb 생성
        
        Args:
            path (list): 네비게이션 경로
            
        Returns:
            str: breadcrumb 문자열
        """
        if not path:
            return "사고 유형 선택"
        
        breadcrumb_items = ["사고 유형"] + path
        return " > ".join(breadcrumb_items)
    
    def get_final_selection_summary(self, path, option):
        """
        최종 선택사항을 요약하여 반환
        
        Args:
            path (list): 네비게이션 경로
            option (str): 선택된 옵션
            
        Returns:
            dict: 선택사항 요약
        """
        return {
            "category_path": path,
            "selected_option": option,
            "breadcrumb": self.build_breadcrumb(path),
            "query_context": f"{' > '.join(path)} > {option}",
            "search_keywords": path + [option]
        }


# 전역 인스턴스 생성
navigation_manager = NavigationDataManager()


def get_navigation_data(path=None):
    """
    네비게이션 데이터를 가져오는 편의 함수
    
    Args:
        path (list): 네비게이션 경로
        
    Returns:
        dict: 네비게이션 데이터
    """
    return navigation_manager.get_navigation_data(path)


def get_final_selection_summary(path, option):
    """
    최종 선택사항 요약을 가져오는 편의 함수
    
    Args:
        path (list): 네비게이션 경로
        option (str): 선택된 옵션
        
    Returns:
        dict: 선택사항 요약
    """
    return navigation_manager.get_final_selection_summary(path, option)