# Cupid's Arrow</br>
연애 소설을 읽으며 누가 이어질지 발을 동동거린 적이 있는가?
그런 당신을 위해 만들었다.</br>

소설 텍스트파일을 입력하면 등장인물 간 관계도를 그래프로 추출하고, </br>그 그래프는 CGCNN과 link prediction을 거쳐 어느 조합이 이어질 가능성이 높은지를 알려준다.</br>
</br>
</br>
### 전반적인 흐름</br>
1. 소설을 넣어 <U>등장인물 간의 관계를 그래프로</U> 추출한다.</br>
   : 그래프의 노드는 등장인물들이며, 엣지는 양쪽 노드(등장인물)가 같이 등장한 횟수, 관계의 긍부정 정도로 표현된다.</br>
2. <U>그래프의 특성을 추출할 CGCNN</U> 을 학습시킬 코드를 짠다.</br>
3. CGCNN 노드별 결과 벡터를 하나의 값으로 만드는 <U>linear transformation</U> 코드를 짠다.</br>
4. 모든 노드 조합의 <U>similarity</U> 값을 dot production으로 구하는 코드를 짠다.</br>
</br>

### 모델 구조
**✓ 그래프의 특성을 학습**</br>
1. edge의 정보까지 고려하는 <U>CGCNN으로 그래프의 중요한 특성 추출을 학습</U>시킨다.</br>
2. output이 각 노드별로 output layer 벡터가 하나씩 나온다.</br>

**✓ 어떤 노드끼리 이어져야하는지**</br>
1. 각 노드들의 벡터를 한번씩 <U>같은 weight, bias로</U> 선형 변환을 함</br>
2. 이렇게 나온 노드들의 벡터를 (여자수*남자수/2)번만큼 <U>dot product로 similarity</U> 계산 -> 결과가 attention value</br>
3. 합이 1이 되게 scaling 거침 (각각이 이어질 확률로 볼 수 있겠다)</br>
4. 가장 큰 값을 가지는 조합을 이어지는 커플로 예측한다.</br>
</br>

### 한계점
- 소설 전체를 넣었기 때문에 누가 이어질지의 내용이 학습할 때 들어가게 된다. 소설을 읽어가면서 전반부를 자를 여유는 없어서 그대로 진행했다.</br>
- 각 조합이 이어질 확률을 출력하면 좋을 것 같으나, scaling을 거친 값들은 편의상 전체 합이 1이 되게 scaling을 거쳐서 만들어진 값이지, 각각이 이어질 확률이라고 보기 어렵다. 이어질 확률을 어떻게 구하면 좋을 지 그 부분은 찬찬히 고민해 볼 예정이다.
