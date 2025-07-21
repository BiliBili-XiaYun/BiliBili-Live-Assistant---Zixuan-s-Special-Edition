def _load_recent_winners_from_persistent(self):
    """
    从持久化中奖用户队列初始化最近中奖用户队列
    """
    self.recent_winners.clear()
    # 从持久化队列中加载最近的10个中奖用户
    recent_persistent = self.persistent_winners[-10:]
    for username in recent_persistent:
        # 查找用户在队列中的索引
        for i, item in enumerate(self.queue_list):
            if item.get('username', '') == username:
                self.recent_winners.append(i)
                break

def _should_exclude_from_lottery(self, username: str) -> bool:
    """
    判断用户是否应该从抽奖中排除
    
    Args:
        username (str): 用户名
    
    Returns:
        bool: True 如果用户应该被排除，False 否则
    """
    # 检查用户是否在最近中奖队列中
    for idx in self.recent_winners:
        if idx < len(self.queue_list) and self.queue_list[idx].get('username', '') == username:
            return True
    
    # 检查用户是否已经上车
    if self.is_user_boarded(username):
        return True
    
    return False

def random_select(self, count: int = 2) -> Tuple[List[int], List[str]]:
    """
    随机选择指定数量的用户，排除最近中奖和已上车的用户
    
    Args:
        count (int): 要选择的用户数量，默认为2
    
    Returns:
        Tuple[List[int], List[str]]: 选中用户的索引列表和用户名列表
    """
    available_users = []
    
    # 获取所有可用用户及其索引
    for i, item in enumerate(self.queue_list):
        username = item.get('username', '')
        
        # 排除最近中奖和已上车的用户
        if not self._should_exclude_from_lottery(username):
            available_users.append((i, username))
    
    # 如果可用用户不足，就使用所有非最近中奖用户
    if len(available_users) < count:
        queue_logger.warning("可选用户数量不足", f"当前可用: {len(available_users)}，请求: {count}")
        return ([], [])
    
    # 使用当前时间戳作为随机种子
    random.seed(datetime.now().timestamp())
    
    # 随机选择用户
    selected = random.sample(available_users, count)
    indices = [i for i, _ in selected]
    usernames = [username for _, username in selected]
    
    # 将选中的用户添加到持久化中奖队列和最近中奖队列
    for i, username in zip(indices, usernames):
        self.add_persistent_winner(username)
        self.recent_winners.append(i)  # 添加到最近中奖队列
    
    queue_logger.info("随机选择结果", str(usernames))
    queue_logger.debug("最近中奖队列长度", str(len(self.recent_winners)))
    return (indices, usernames)
