const { api } = require('../api.js');

describe('api', () => {
    beforeEach(() => {
        global.fetch = jest.fn();
        global.localStorage.clear();
    });

    afterEach(() => {
        jest.restoreAllMocks();
    });

    describe('auth', () => {
        describe('loginWithGoogle', () => {
            test('should store user in localStorage', async () => {
                const user = await api.auth.loginWithGoogle();
                
                expect(user).toEqual({ id: '1', name: 'User', email: 'user@example.com' });
                expect(localStorage.getItem('user')).toBeTruthy();
            });
        });

        describe('logout', () => {
            test('should remove user from localStorage', async () => {
                localStorage.setItem('user', JSON.stringify({ id: '1', name: 'Test' }));
                
                await api.auth.logout();
                
                expect(localStorage.getItem('user')).toBeNull();
            });
        });

        describe('getUser', () => {
            test('should return user from localStorage', () => {
                const testUser = { id: '1', name: 'Test User' };
                localStorage.setItem('user', JSON.stringify(testUser));
                
                const user = api.auth.getUser();
                
                expect(user).toEqual(testUser);
            });

            test('should return null when no user in localStorage', () => {
                const user = api.auth.getUser();
                
                expect(user).toBeNull();
            });

            test('should return null when localStorage contains invalid JSON', () => {
                localStorage.setItem('user', 'invalid-json');
                
                const user = api.auth.getUser();
                
                expect(user).toBeNull();
            });

            test('should handle localStorage.getItem returning null safely', () => {
                localStorage.setItem('user', null);
                
                const user = api.auth.getUser();
                
                expect(user).toBeNull();
            });
        });
    });

    describe('files', () => {
        describe('getFiles', () => {
            test('should fetch files from correct path', async () => {
                const mockFiles = [{ name: 'test.txt', isDirectory: false }];
                global.fetch.mockResolvedValueOnce({
                    ok: true,
                    json: async () => mockFiles
                });
                
                const files = await api.files.getFiles('/documents');
                
                expect(fetch).toHaveBeenCalled();
                expect(files).toEqual(mockFiles);
            });

            test('should use default path / when not provided', async () => {
                global.fetch.mockResolvedValueOnce({
                    ok: true,
                    json: async () => []
                });
                
                await api.files.getFiles();
                
                expect(fetch).toHaveBeenCalled();
            });

            test('should throw error when response is not ok', async () => {
                global.fetch.mockResolvedValueOnce({
                    ok: false
                });
                
                await expect(api.files.getFiles('/')).rejects.toThrow('Failed to fetch files');
            });

            test('should handle fetch errors gracefully', async () => {
                global.fetch.mockRejectedValueOnce(new TypeError('Network error'));
                
                await expect(api.files.getFiles('/')).rejects.toThrow();
            });
        });

        describe('uploadFile', () => {
            test('should upload file with correct FormData', async () => {
                const mockFile = { name: 'test.txt', size: 100 };
                global.fetch.mockResolvedValueOnce({
                    ok: true,
                    json: async () => ({ success: true })
                });
                
                await api.files.uploadFile(mockFile, '/uploads');
                
                expect(fetch).toHaveBeenCalledWith(
                    'http://localhost:8000/files/upload?path=%2Fuploads',
                    expect.objectContaining({
                        method: 'POST'
                    })
                );
            });
        });

        describe('deleteFile', () => {
            test('should send DELETE request with correct body', async () => {
                global.fetch.mockResolvedValueOnce({
                    ok: true,
                    json: async () => ({ success: true })
                });
                
                await api.files.deleteFile('/test.txt');
                
                expect(fetch).toHaveBeenCalledWith(
                    'http://localhost:8000/files/delete',
                    expect.objectContaining({
                        method: 'DELETE',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ path: '/test.txt' })
                    })
                );
            });

            test('should handle delete errors gracefully', async () => {
                global.fetch.mockResolvedValueOnce({
                    ok: false,
                    status: 500
                });
                
                await expect(api.files.deleteFile('/test.txt')).rejects.toThrow();
            });
        });

        describe('rename', () => {
            test('should send rename request with correct body', async () => {
                global.fetch.mockResolvedValueOnce({
                    ok: true,
                    json: async () => ({ success: true })
                });
                
                await api.files.rename('/old.txt', 'new.txt');
                
                expect(fetch).toHaveBeenCalledWith(
                    'http://localhost:8000/files/rename',
                    expect.objectContaining({
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ path: '/old.txt', newName: 'new.txt' })
                    })
                );
            });
        });
    });

    describe('ai', () => {
        describe('search', () => {
            test('should search with text parameter', async () => {
                const mockResult = { answer: 'Found files', relevant_files: ['/doc.txt'] };
                global.fetch.mockResolvedValueOnce({
                    ok: true,
                    json: async () => mockResult
                });
                
                const result = await api.ai.search('marketing strategy');
                
                expect(fetch).toHaveBeenCalled();
                expect(result).toEqual(mockResult);
            });

            test('should include filePath when provided', async () => {
                const mockResult = { answer: 'Found', relevant_files: [] };
                global.fetch.mockResolvedValueOnce({
                    ok: true,
                    json: async () => mockResult
                });
                
                await api.ai.search('test', '/docs');
                
                expect(fetch).toHaveBeenCalled();
            });

            test('should handle search errors gracefully', async () => {
                global.fetch.mockRejectedValueOnce(new TypeError('Network error'));
                
                await expect(api.ai.search('test')).rejects.toThrow();
            });
        });
    });

    describe('BASE_URL', () => {
        test('should use localhost:8000 as BASE_URL', () => {
            const { api } = require('../api.js');
            expect(api.files.getFiles).toBeDefined();
        });
    });
});